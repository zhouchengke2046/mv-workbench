#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TokenTech / new-api video adapter (Muse / OpenAI-style /v1/videos).

Text-to-video is tested. Reference-image field is NOT verified; pass
--image-field explicitly if you want to test one.

Never prints the API key.
"""
import argparse
import json
import os
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


def load_router():
    cfg, _ = mv_keys.load_cfg()
    router = cfg.get("router") or {}
    key = (os.environ.get("ROUTER_API_KEY") or os.environ.get("APIMART_KEY") or router.get("api_key") or "").strip()
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


def task_id_of(data):
    if not isinstance(data, dict):
        return None
    for k in ("id", "task_id", "video_id"):
        if data.get(k):
            return str(data[k])
    inner = data.get("data")
    if isinstance(inner, dict):
        for k in ("id", "task_id", "video_id"):
            if inner.get(k):
                return str(inner[k])
    return None


def download(url, key, target, proxy="", with_auth=True):
    headers = {"Accept": "*/*"}
    if with_auth:
        headers["Authorization"] = "Bearer " + key
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=headers, method="GET")
    with opener.open(req, timeout=180) as resp:
        target.write_bytes(resp.read())
    return target.stat().st_size


def main():
    parser = argparse.ArgumentParser(description="Generate a Muse video via Router /v1/videos")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--size", default="720x1280")
    parser.add_argument("--resolution", default="720p")
    parser.add_argument("--out", default="")
    parser.add_argument("--image-urls", nargs="*", default=[])
    parser.add_argument("--image-field", choices=["image_urls", "input_reference", "image"], default=None)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--poll-limit", type=int, default=150)
    args = parser.parse_args()

    key, base, proxy = load_router()
    if not key:
        raise SystemExit("Router key 未配置：先运行 mvwb keys set router")
    if args.image_urls and not args.image_field:
        raise SystemExit("参考图字段未验证：请显式传 --image-field image_urls|input_reference|image")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.out).expanduser() if args.out else (Path("out") / ("muse_" + stamp + ".mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    meta_dir = out.parent / (out.stem + "_meta")
    meta_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": "muse-video-ext",
        "prompt": args.prompt,
        "seconds": args.seconds,
        "resolution": args.resolution,
        "size": args.size,
    }
    if args.image_urls:
        if args.image_field == "image":
            payload["image"] = args.image_urls[0]
        else:
            payload[args.image_field] = list(args.image_urls)

    print("submit: seconds=%s size=%s resolution=%s" % (args.seconds, args.size, args.resolution))
    if args.image_urls:
        print("WARNING: reference-image field %r is unverified; 400 does not charge, 200 creates a paid task" % args.image_field)
    status, data = request_json(base + "/v1/videos", key, "POST", payload, proxy, args.timeout)
    (meta_dir / "submit.json").write_text(
        json.dumps({"status": status, "response": data, "payload": payload}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if status != 200:
        print("submit failed HTTP %s: %s" % (status, error_text(data)))
        return 2
    task_id = task_id_of(data)
    if not task_id:
        print("submit returned no id: %s" % json.dumps(data, ensure_ascii=False)[:500])
        return 2
    print("task:", task_id)

    final = None
    for i in range(args.poll_limit):
        status, data = request_json(base + "/v1/videos/" + task_id, key, proxy=proxy, timeout=args.timeout)
        state = data.get("status") if isinstance(data, dict) else None
        if not state and isinstance(data.get("data"), dict):
            state = data["data"].get("status")
        print("[%02d] http=%s status=%s" % (i + 1, status, state))
        (meta_dir / "last_status.json").write_text(
            json.dumps({"http": status, "response": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if state in ("completed", "succeeded", "success"):
            final = data
            break
        if state in ("failed", "error", "cancelled", "canceled"):
            print("failed:", error_text(data))
            return 3
        time.sleep(args.poll_interval)
    if final is None:
        print("timeout waiting for completion")
        return 4

    print("download:", out)
    try:
        size = download(base + "/v1/videos/" + task_id + "/content", key, out, proxy)
        print("saved %s bytes" % size)
    except Exception as exc:
        print("download failed:", type(exc).__name__, exc)
        return 5

    meta = {
        "task_id": task_id,
        "request": payload,
        "final": final,
        "video": str(out),
        "bytes": out.stat().st_size,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (meta_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
