#!/usr/bin/env python3
"""RunningHub 统一运行器（MV工作台）：AI应用/workflow 两形态 + 上传 + 轮询 + 下载 + 记账输出

用法：
  AI应用:   python3 rh_run.py --app <webappId> --name <tag> --overrides ov.json [--out DIR] [--timeout 1800]
  workflow: python3 rh_run.py --wf <workflowId> --name <tag> --nodes nodes.json [--out DIR] ...
  上传:     python3 rh_run.py --upload <文件>     # 输出 api/<hash>.<ext>，填回 nodes/overrides（保留 api/ 前缀）

overrides 键格式 "节点ID:字段名"，如 {"114:text": "...", "116:value": "45"}。
nodes.json 为部分节点列表 [{"nodeId","fieldName","fieldValue"}]（RH 允许只传要改的节点）。
key 由 mvwb/mv_keys.py 注入 RUNNINGHUB_API_KEY；共享 key 未经允许不使用。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
from console import setup  # noqa: E402
setup()

BASE = "https://www.runninghub.cn"


def load_key():
    key = os.environ.get("RUNNINGHUB_API_KEY", "").strip()
    if not key:
        sys.exit("[!] 未配置 RunningHub key；运行 mvwb keys set runninghub，或由 mv_keys.py exec 注入 RUNNINGHUB_API_KEY")
    return key


def fail(msg, detail=""):
    print("[!] %s" % msg, file=sys.stderr)
    if detail:
        print("    接口返回：%s" % str(detail)[:500].replace("\n", " "), file=sys.stderr)
    sys.exit(1)


def read_json(req, timeout=60):
    """统一处理 HTTP/网络/JSON 错误，避免把原始 traceback 丢给用户。"""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        fail("RunningHub 返回 HTTP %s" % exc.code, raw)
    except urllib.error.URLError as exc:
        fail("连不上 RunningHub（%s）" % exc.reason,
             "检查网络、代理或防火墙；RunningHub 国内通常可直连")
    except (TimeoutError, OSError) as exc:
        fail("请求 RunningHub 超时或中断（%s）" % exc,
             "稍后重试；持续失败先运行 mvwb doctor --network")
    try:
        return json.loads(raw)
    except ValueError:
        fail("RunningHub 返回的不是 JSON", raw)


def post(path, payload, key=None, bearer=False):
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer %s" % key
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers=headers)
    return read_json(req)


def explain_business_error(resp, what="请求"):
    """把常见业务错误翻译成可执行的下一步；不猜具体错误码含义。"""
    code = resp.get("code") if isinstance(resp, dict) else None
    msg = (resp.get("msg") or resp.get("message") or "") if isinstance(resp, dict) else ""
    tips = []
    text = ("%s %s" % (code, msg)).lower()
    if any(k in text for k in ("332", "user_does_not_exist", "user does not exist", "401", "unauthorized")):
        tips.append("Key 可能无效、过期或不属于当前账号；运行 mvwb keys set runninghub 重新配置")
    if any(k in text for k in ("805", "901", "not found", "not_exists", "no permission", "forbidden", "403")):
        tips.append("应用/工作流 ID 可能不对，或当前账号没有权限；确认 --app 是 AI 应用 ID（不是 workflow ID）")
    if any(k in text for k in ("insufficient", "balance", "coin", "余额", "币")):
        tips.append("余额不足；运行 mvwb keys balance 查余额后充值")
    if not tips:
        tips.append("检查 Key、应用/工作流 ID、账号权限；完整返回见上")
    return "%s失败：%s" % (what, "；".join(tips))


def upload(path, key):
    """POST /task/openapi/upload（multipart）。返回 api/<hash>.<ext>，前缀必须保留。"""
    fn = os.path.basename(path)
    ext = os.path.splitext(fn)[1].lstrip(".") or "bin"
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in (("apiKey", key), ("fileName", "api/" + fn), ("fileType", ext)):
        body += ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                 % (boundary, k, v)).encode()
    body += ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
             'Content-Type: application/octet-stream\r\n\r\n' % (boundary, fn)).encode()
    try:
        with open(path, "rb") as fh:
            file_bytes = fh.read()
    except OSError as exc:
        fail("读不到要上传的文件：%s" % path, exc)
    body += file_bytes + ("\r\n--%s--\r\n" % boundary).encode()
    req = urllib.request.Request(BASE + "/task/openapi/upload", data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    r = read_json(req, timeout=120)
    if r.get("code") != 0:
        fail(explain_business_error(r, "上传"), json.dumps(r, ensure_ascii=False))
    data = r.get("data")
    if not isinstance(data, str) or not data:
        fail("上传接口没有返回文件路径", json.dumps(r, ensure_ascii=False))
    print("[upload] %s -> %s" % (path, data))
    return data


def apply_overrides(nodes, ov):
    hit = 0
    for n in nodes:
        k = (str(n.get("nodeId")), n.get("fieldName"))
        if k in ov:
            n["fieldValue"] = ov[k]
            hit += 1
    missed = set(ov) - set((str(n.get("nodeId")), n.get("fieldName")) for n in nodes)
    if missed:
        print("[warn] 这些节点字段在 demo 里没找到: %s" % sorted(missed))
    return hit


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app", help="AI 应用 webappId")
    g.add_argument("--wf", help="workflow ID")
    g.add_argument("--upload", help="要上传的本地文件")
    ap.add_argument("--name", default="task")
    ap.add_argument("--overrides", help="AI应用覆盖参数 JSON：{节点:字段: 值}")
    ap.add_argument("--nodes", help="workflow 节点列表 JSON")
    ap.add_argument("--out", default=".", help="产物下载目录")
    ap.add_argument("--timeout", type=int, default=1500, help="轮询上限秒")
    ap.add_argument("--interval", type=int, default=20)
    args = ap.parse_args()
    key = load_key()

    if args.upload:
        upload(args.upload, key)
        return

    os.makedirs(args.out, exist_ok=True)
    if args.app:
        demo_url = "%s/api/webapp/apiCallDemo?apiKey=%s&webappId=%s" % (BASE, key, args.app)
        demo = read_json(urllib.request.Request(demo_url), timeout=60)
        data = demo.get("data") if isinstance(demo, dict) else None
        if not isinstance(data, dict) or not isinstance(data.get("nodeInfoList"), list):
            fail(explain_business_error(demo, "读取 AI 应用参数"),
                 "没有返回 nodeInfoList；" + json.dumps(demo, ensure_ascii=False))
        nodes = data["nodeInfoList"]
        if args.overrides:
            try:
                with open(args.overrides, encoding="utf-8") as fh:
                    ov = {tuple(k.split(":", 1)): v for k, v in json.load(fh).items()}
            except (OSError, ValueError) as exc:
                fail("overrides 文件读取失败：%s" % args.overrides, exc)
            apply_overrides(nodes, ov)
        r = post("/openapi/v2/run/ai-app/%s" % args.app,
                 {"nodeInfoList": nodes, "instanceType": "default", "usePersonalQueue": "false"},
                 key=key, bearer=True)
        tid = r.get("taskId") or (r.get("data") or {}).get("taskId")
        if not tid:
            fail(explain_business_error(r, "提交任务"), json.dumps(r, ensure_ascii=False))
    else:
        try:
            with open(args.nodes, encoding="utf-8") as fh:
                nodes = json.load(fh)
        except (OSError, ValueError) as exc:
            fail("nodes 文件读取失败：%s" % args.nodes, exc)
        if isinstance(nodes, dict) and "nodeInfoList" in nodes:
            nodes = nodes["nodeInfoList"]
        if not isinstance(nodes, list):
            fail("nodes 文件格式不对：应为节点数组，或 {nodeInfoList: [...]}", args.nodes)
        r = post("/task/openapi/create",
                 {"apiKey": key, "workflowId": args.wf, "nodeInfoList": nodes,
                  "instanceType": "default"})
        if r.get("code") != 0:
            fail(explain_business_error(r, "提交任务"), json.dumps(r, ensure_ascii=False))
        tid = (r.get("data") or {}).get("taskId")
        if not tid:
            fail("提交成功但接口没有返回 taskId", json.dumps(r, ensure_ascii=False))
    print("[%s] taskId=%s" % (args.name, tid))

    t0 = time.time()
    while True:
        time.sleep(args.interval)
        s = post("/task/openapi/status", {"apiKey": key, "taskId": tid})
        if s.get("code") != 0:
            fail(explain_business_error(s, "查询任务状态"), json.dumps(s, ensure_ascii=False))
        d = s.get("data")
        stt = d.get("taskStatus") if isinstance(d, dict) else d
        print("[%s] %ds %s" % (args.name, int(time.time() - t0), stt), flush=True)
        if stt in ("SUCCESS", "FAILED", "CANCELLED"):
            break
        if time.time() - t0 > args.timeout:
            print("[%s] TIMEOUT（任务可能仍在跑，拿 taskId 手动查）task=%s" % (args.name, tid))
            return

    o = post("/task/openapi/outputs", {"apiKey": key, "taskId": tid})
    if o.get("code") != 0:
        fail(explain_business_error(o, "获取产物"), json.dumps(o, ensure_ascii=False))
    print("[%s] outputs code=%s" % (args.name, o.get("code")))
    coins, saved = 0, []
    files = o.get("data") or []
    if not isinstance(files, list):
        fail("产物格式不对：data 应为文件数组", json.dumps(o, ensure_ascii=False))
    for i, f in enumerate(files):
        if not isinstance(f, dict):
            continue
        c = f.get("consumeCoins") or 0
        coins += c
        u = f.get("fileUrl") or ""
        print("  node=%s type=%s coins=%s %s" % (f.get("nodeId"), f.get("fileType"), c, u[:100]))
        if u:
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".bin"
            fn = os.path.join(args.out, "%s_%d%s" % (args.name, i, ext) if len(files) > 1
                              else "%s%s" % (args.name, ext))
            try:
                urllib.request.urlretrieve(u, fn)
            except (urllib.error.URLError, OSError) as exc:
                print("[warn] 下载失败 %s：%s" % (u[:100], exc), file=sys.stderr)
                continue
            saved.append(fn)
            print("    saved -> %s" % fn)
    json.dump(o, open(os.path.join(args.out, "%s_result.json" % args.name), "w"),
              ensure_ascii=False, indent=1)
    print("[记账] 实际消耗 %s 币 · 产物 %d 个 · taskId=%s（写入 cost.log 由 AI 完成）" % (coins, len(saved), tid))


if __name__ == "__main__":
    main()
