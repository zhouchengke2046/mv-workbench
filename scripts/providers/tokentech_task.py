#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TokenTech / new-api task adapter (moss 图 / ace 音乐, OpenAI Responses 协议).

实测契约（2026-11-14，router.kcacher.top）：

    POST /v1/responses
    {"model": "moss-t2i-rh-ck", "input": "...", "background": true,
     "metadata": {"nodeInfoList": [{"nodeId": "4", "fieldName": "text",
                                    "fieldValue": "<主提示词>"}, ...]}}

- 参数只认 metadata.nodeInfoList（直通 RunningHub 工作流节点）；
  有 nodeInfoList 时 input 不再映射歌词，歌词必须写进 115 节点。
- moss：4=主提示词 text，5=负向 text，16=seed。
- ace：114=风格 text，115=歌词 text，116=时长(秒) value，117=BPM value，
  94=language/keyscale/timesignature（默认 zh / C major / 4，未单测）。
- 轮询 GET /v1/responses/{id}，产物 = GET output 里的 artifact URL（带 ?access=）。
- 计费按 RH 实际运行时长扣，金额以账单为准。

Never prints the API key.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
import mv_keys  # noqa: E402
import alerts  # noqa: E402
from console import setup  # noqa: E402
setup()

PLATFORM = "router"

MODELS = {
    "image": {
        "model": "moss-t2i-rh-ck",
        "nodes": {"prompt": ("4", "text"), "negative": ("5", "text"), "seed": ("16", "seed")},
    },
    "music": {
        "model": "ace-step-1.5-rh-ck",
        "nodes": {
            "style": ("114", "text"),
            "lyrics": ("115", "text"),
            "seconds": ("116", "value"),
            "bpm": ("117", "value"),
            "language": ("94", "language"),
            "keyscale": ("94", "keyscale"),
            "timesignature": ("94", "timesignature"),
        },
    },
}

ARTIFACT_RE = re.compile(r'src="([^"]+)"')


def http_alert(status):
    if status in (401, 403):
        return "P1"
    if status == 402:
        return "P2"
    return "P5" if status in (408, 429, 500, 502, 503, 504) else "P3"


def load_router():
    cfg, _ = mv_keys.load_cfg()
    router = cfg.get("router") or {}
    key = (os.environ.get("ROUTER_API_KEY") or router.get("api_key") or "").strip()
    base = (router.get("base_url") or "https://router.kcacher.top").rstrip("/")
    proxy = (router.get("proxy") or "").strip()
    return key, base, proxy


def request_json(url, key, method="GET", payload=None, proxy="", timeout=30):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw[:800]}
        return exc.code, data
    except Exception as exc:
        return None, {"error": "%s: %s" % (type(exc).__name__, exc)}


def error_text(data):
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err)
        if err:
            return str(err)
        return str(data.get("message") or data)[:500]
    return str(data)[:500]


def download(url, key, target, proxy=""):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + key, "Accept": "*/*"}, method="GET")
    with opener.open(req, timeout=180) as resp:
        target.write_bytes(resp.read())
    return target.stat().st_size


def build_payload(kind, values):
    spec = MODELS[kind]
    node_list = []
    for name, (node_id, field) in spec["nodes"].items():
        if name in values and values[name] is not None:
            node_list.append({
                "nodeId": node_id,
                "fieldName": field,
                "fieldValue": values[name],
            })
    return {
        "model": spec["model"],
        "input": values.get("prompt") or values.get("lyrics") or " ",
        "background": True,
        "metadata": {"nodeInfoList": node_list},
    }


def main():
    parser = argparse.ArgumentParser(description="moss 生图 / ace 生音乐（Router /v1/responses 任务协议）")
    sub = parser.add_subparsers(dest="kind", required=True)

    p_img = sub.add_parser("image", help="moss-t2i-rh-ck 生图")
    p_img.add_argument("--prompt", required=True)
    p_img.add_argument("--negative", default="blurry, deformed, watermark")
    p_img.add_argument("--seed", type=int, default=None)
    p_img.add_argument("--out", default="")

    p_mus = sub.add_parser("music", help="ace-step-1.5-rh-ck 生音乐")
    p_mus.add_argument("--lyrics", required=True)
    p_mus.add_argument("--style", required=True)
    p_mus.add_argument("--seconds", type=float, default=None)
    p_mus.add_argument("--bpm", type=int, default=None)
    p_mus.add_argument("--language", default=None)
    p_mus.add_argument("--keyscale", default=None)
    p_mus.add_argument("--timesignature", default=None)
    p_mus.add_argument("--out", default="")

    for p in (p_img, p_mus):
        p.add_argument("--timeout", type=int, default=30)
        p.add_argument("--poll-interval", type=int, default=6)
        p.add_argument("--poll-limit", type=int, default=100)

    args = parser.parse_args()
    kind = args.kind
    model = MODELS[kind]["model"]

    key, base, proxy = load_router()
    if not key:
        alerts.fail("K001", "Router key 未配置：先运行 mvwb keys set router，或导入老师发的 zz-keys.json", platform=PLATFORM)

    if kind == "image":
        values = {"prompt": args.prompt, "negative": args.negative, "seed": args.seed}
        suffix = ".png"
    else:
        values = {
            "lyrics": args.lyrics, "style": args.style, "seconds": args.seconds,
            "bpm": args.bpm, "language": args.language, "keyscale": args.keyscale,
            "timesignature": args.timesignature,
        }
        suffix = ".mp3"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.out).expanduser() if args.out else (Path("out") / ("%s_%s%s" % (kind, stamp, suffix)))
    out.parent.mkdir(parents=True, exist_ok=True)
    meta_dir = out.parent / (out.stem + "_meta")
    meta_dir.mkdir(parents=True, exist_ok=True)

    payload = build_payload(kind, values)
    print("submit: model=%s nodes=%s" % (model, ",".join("%s:%s" % (n["nodeId"], n["fieldName"]) for n in payload["metadata"]["nodeInfoList"])))
    status, data = request_json(base + "/v1/responses", key, "POST", payload, proxy, args.timeout)
    (meta_dir / "submit.json").write_text(
        json.dumps({"status": status, "response": data, "payload": payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if status != 200:
        alerts.fail(http_alert(status), "submit HTTP %s: %s" % (status, error_text(data)),
                    platform=PLATFORM, model=model, error_class="submit", raw=json.dumps(data, ensure_ascii=False)[:300])
    rid = str(data.get("id") or "")
    if not rid:
        alerts.fail("P3", "submit 返回没有 response id：%s" % json.dumps(data, ensure_ascii=False)[:500],
                    platform=PLATFORM, model=model, error_class="submit")
    task_id = str((data.get("metadata") or {}).get("task_id") or "")
    print("response:", rid, "task:", task_id)

    final = None
    for i in range(args.poll_limit):
        status, data = request_json(base + "/v1/responses/" + rid, key, proxy=proxy, timeout=args.timeout)
        state = data.get("status") if isinstance(data, dict) else None
        print("[%02d] http=%s status=%s" % (i + 1, status, state))
        (meta_dir / "last_status.json").write_text(
            json.dumps({"http": status, "response": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if state == "completed":
            final = data
            break
        if state in ("failed", "incomplete", "cancelled"):
            alerts.fail("P4", "任务 %s 状态=%s：%s" % (task_id or rid, state, error_text(data)),
                        platform=PLATFORM, model=model, error_class="task_failed",
                        raw=json.dumps(data, ensure_ascii=False)[:300])
        time.sleep(args.poll_interval)
    if final is None:
        alerts.fail("P5", "轮询 %d 次仍未完成（task=%s）" % (args.poll_limit, task_id or rid),
                    platform=PLATFORM, model=model, error_class="poll_timeout")

    outputs = final.get("output") or []
    text = ""
    if outputs:
        content = outputs[0].get("content") or []
        if content:
            text = str(content[0].get("text") or "")
    match = ARTIFACT_RE.search(text)
    if not match:
        alerts.fail("P6", "产物地址未找到（task=%s）：%s" % (task_id or rid, text[:300]),
                    platform=PLATFORM, model=model, error_class="download")
    artifact_url = match.group(1)

    print("download:", out)
    size = 0
    for attempt in range(4):
        try:
            size = download(artifact_url, key, out, proxy)
            break
        except Exception as exc:
            if attempt == 3:
                alerts.fail("P6", "下载失败（task=%s）：%s: %s" % (task_id or rid, type(exc).__name__, exc),
                            platform=PLATFORM, model=model, error_class="download")
            time.sleep(3)
    print("saved %s bytes" % size)

    meta = {
        "response_id": rid,
        "task_id": task_id,
        "request": payload,
        "final": final,
        "artifact_url": artifact_url,
        "file": str(out),
        "bytes": size,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (meta_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
