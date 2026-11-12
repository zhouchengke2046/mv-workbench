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
import urllib.parse
import urllib.request
import uuid

BASE = "https://www.runninghub.cn"


def load_key():
    key = os.environ.get("RUNNINGHUB_API_KEY", "").strip()
    if not key:
        sys.exit("[!] 未配置 RunningHub key；运行 mvwb keys set runninghub，或由 mv_keys.py exec 注入 RUNNINGHUB_API_KEY")
    return key


def post(path, payload, key=None, bearer=False):
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer %s" % key
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=60))


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
    body += open(path, "rb").read() + ("\r\n--%s--\r\n" % boundary).encode()
    req = urllib.request.Request(BASE + "/task/openapi/upload", data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if r.get("code") != 0:
        sys.exit("[!] 上传失败: %s" % json.dumps(r, ensure_ascii=False)[:300])
    print("[upload] %s -> %s" % (path, r["data"]))
    return r["data"]


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
        demo = json.load(urllib.request.urlopen(demo_url, timeout=60))["data"]
        nodes = demo["nodeInfoList"]
        if args.overrides:
            ov = {tuple(k.split(":", 1)): v for k, v in json.load(open(args.overrides)).items()}
            apply_overrides(nodes, ov)
        r = post("/openapi/v2/run/ai-app/%s" % args.app,
                 {"nodeInfoList": nodes, "instanceType": "default", "usePersonalQueue": "false"},
                 key=key, bearer=True)
        tid = r.get("taskId") or (r.get("data") or {}).get("taskId")
        if not tid:
            sys.exit("[!] 提交失败: %s" % json.dumps(r, ensure_ascii=False)[:400])
    else:
        nodes = json.load(open(args.nodes))
        if isinstance(nodes, dict) and "nodeInfoList" in nodes:
            nodes = nodes["nodeInfoList"]
        r = post("/task/openapi/create",
                 {"apiKey": key, "workflowId": args.wf, "nodeInfoList": nodes,
                  "instanceType": "default"})
        if r.get("code") != 0:
            sys.exit("[!] 提交失败: %s" % json.dumps(r, ensure_ascii=False)[:400])
        tid = r["data"]["taskId"]
    print("[%s] taskId=%s" % (args.name, tid))

    t0 = time.time()
    while True:
        time.sleep(args.interval)
        s = post("/task/openapi/status", {"apiKey": key, "taskId": tid})
        d = s.get("data")
        stt = d.get("taskStatus") if isinstance(d, dict) else d
        print("[%s] %ds %s" % (args.name, int(time.time() - t0), stt), flush=True)
        if stt in ("SUCCESS", "FAILED", "CANCELLED"):
            break
        if time.time() - t0 > args.timeout:
            print("[%s] TIMEOUT（任务可能仍在跑，拿 taskId 手动查）task=%s" % (args.name, tid))
            return

    o = post("/task/openapi/outputs", {"apiKey": key, "taskId": tid})
    print("[%s] outputs code=%s" % (args.name, o.get("code")))
    coins, saved = 0, []
    files = o.get("data") or []
    for i, f in enumerate(files):
        c = f.get("consumeCoins") or 0
        coins += c
        u = f.get("fileUrl") or ""
        print("  node=%s type=%s coins=%s %s" % (f.get("nodeId"), f.get("fileType"), c, u[:100]))
        if u:
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".bin"
            fn = os.path.join(args.out, "%s_%d%s" % (args.name, i, ext) if len(files) > 1
                              else "%s%s" % (args.name, ext))
            urllib.request.urlretrieve(u, fn)
            saved.append(fn)
            print("    saved -> %s" % fn)
    json.dump(o, open(os.path.join(args.out, "%s_result.json" % args.name), "w"),
              ensure_ascii=False, indent=1)
    print("[记账] 实际消耗 %s 币 · 产物 %d 个 · taskId=%s（写入 cost.log 由 AI 完成）" % (coins, len(saved), tid))


if __name__ == "__main__":
    main()
