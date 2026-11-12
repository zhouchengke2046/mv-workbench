#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 工作台本地配置服务（只绑定 127.0.0.1）。

功能：
- 托管 workbench.html 与项目静态文件（支持 Range，音视频可拖进度条）
- GET  /api/keys     掩码状态（绝不返回原始 key）
- POST /api/keys     写入 ~/.config/mv-workbench/keys.json（0600）
- GET  /api/balance  查询 RunningHub / Router 余额
- GET  /api/health

服务版 HTML 会注入“配置 Key”按钮/弹窗；直接 file:// 打开的静态版不注入。
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mv_keys  # noqa: E402
from console import setup  # noqa: E402
setup()

UI_JS_PATH = HERE / "mv_keys_ui.js"
MAX_BODY = 64 * 1024
CHUNK = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    root = Path("/")
    workbench_abs = Path("/")
    workbench_rel = ""
    balance_timeout = 12
    server_version = "MVKeys/1.0"
    sys_version = ""

    # ---------- low level ----------
    def log_message(self, fmt, *args):
        # 不记录请求体/查询串，避免 key 进入日志
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _origin_ok(self):
        origin = (self.headers.get("Origin") or "").strip()
        if not origin:
            return True
        port = self.server.server_port
        allowed = {
            "http://127.0.0.1:%d" % port,
            "http://localhost:%d" % port,
        }
        return origin in allowed

    # ---------- api ----------
    def _keys_status(self):
        cfg, _ = mv_keys.load_cfg()
        rh = cfg.get("runninghub") or {}
        rt = cfg.get("router") or {}
        return {
            "ok": True,
            "keys_path": str(mv_keys.keys_path()),
            "runninghub": {
                "configured": bool((rh.get("api_key") or "").strip()),
                "masked": mv_keys.mask(rh.get("api_key")),
                "label": rh.get("label") or "RunningHub",
                "account": rh.get("account") or "",
            },
            "router": {
                "configured": bool((rt.get("api_key") or "").strip()),
                "masked": mv_keys.mask(rt.get("api_key")),
                "label": rt.get("label") or "Router",
                "provider": rt.get("provider") or "",
                "base_url": rt.get("base_url") or "",
                "balance_mode": rt.get("balance_mode") or "newapi",
                "proxy_set": bool((rt.get("proxy") or "").strip()),
            },
        }

    def _update_keys(self, payload):
        cfg, _ = mv_keys.load_cfg()
        rh = payload.get("runninghub") if isinstance(payload.get("runninghub"), dict) else {}
        rt = payload.get("router") if isinstance(payload.get("router"), dict) else {}

        if rh.get("clear"):
            cfg["runninghub"]["api_key"] = ""
        else:
            key = str(rh.get("api_key") or "").strip()
            if key:
                if len(key) > 500 or any(ch in key for ch in "\r\n\t"):
                    raise ValueError("RunningHub Key 格式不正确")
                cfg["runninghub"]["api_key"] = key
        if "account" in rh:
            cfg["runninghub"]["account"] = str(rh.get("account") or "").strip()[:120]

        if rt.get("clear"):
            cfg["router"]["api_key"] = ""
        else:
            key = str(rt.get("api_key") or "").strip()
            if key:
                if len(key) > 500 or any(ch in key for ch in "\r\n\t"):
                    raise ValueError("Router Key 格式不正确")
                cfg["router"]["api_key"] = key

        base_url = str(rt.get("base_url") or "").strip().rstrip("/")
        if base_url:
            if len(base_url) > 500 or not re.match(r"^https?://[^\s]+$", base_url):
                raise ValueError("Base URL 必须是 http(s):// 地址")
            cfg["router"]["base_url"] = base_url

        provider = str(rt.get("provider") or "").strip()
        if provider:
            if len(provider) > 50:
                raise ValueError("Router 类型过长")
            cfg["router"]["provider"] = provider

        mode = str(rt.get("balance_mode") or "").strip().lower()
        if mode:
            if mode not in ("newapi", "openai"):
                raise ValueError("余额模式只能是 newapi 或 openai")
            cfg["router"]["balance_mode"] = mode

        if rt.get("clear_proxy"):
            cfg["router"]["proxy"] = ""
        else:
            proxy = str(rt.get("proxy") or "").strip()
            if proxy:
                if len(proxy) > 500 or not re.match(r"^https?://[^\s]+$", proxy):
                    raise ValueError("代理必须是 http(s):// 地址")
                cfg["router"]["proxy"] = proxy

        mv_keys.save_cfg(cfg)
        return self._keys_status()

    def _balance(self):
        cfg, _ = mv_keys.load_cfg()
        checked_at = mv_keys.now_iso()
        payload = {
            "checked_at": checked_at,
            "keys_path": str(mv_keys.keys_path()),
            "runninghub": mv_keys.balance_runninghub(cfg, self.balance_timeout),
            "router": mv_keys.balance_router(cfg, self.balance_timeout),
        }
        return {
            "ok": True,
            "checked_at": checked_at,
            "keys": mv_keys.to_data_keys(payload),
        }

    # ---------- static ----------
    def _safe_path(self, url_path):
        rel = url_path.lstrip("/")
        candidate = (self.root / rel).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            return None
        try:
            parts = candidate.relative_to(self.root).parts
        except ValueError:
            return None
        if any(part.startswith(".") for part in parts):
            return None
        return candidate

    def _serve_workbench(self, path, head_only=False):
        html = path.read_text(encoding="utf-8")
        flag = "<script>window.MV_SERVER_MODE=true;</script>"
        if flag not in html:
            if "</head>" in html:
                html = html.replace("</head>", flag + "</head>", 1)
            else:
                html = flag + html
        if "MV_KEY_UI" not in html and UI_JS_PATH.exists():
            ui = UI_JS_PATH.read_text(encoding="utf-8")
            if "</body>" in html:
                html = html.replace("</body>", "<script>\n" + ui + "\n</script></body>", 1)
            else:
                html += "<script>\n" + ui + "\n</script>"
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _serve_file(self, path, head_only=False):
        try:
            size = path.stat().st_size
        except OSError:
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        start = 0
        end = size - 1
        status = 200
        range_header = (self.headers.get("Range") or "").strip()
        if range_header:
            match = re.match(r"bytes=(\d*)-(\d*)$", range_header)
            if not match:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            start_s, end_s = match.groups()
            if not start_s:
                suffix = int(end_s or 0)
                start = max(0, size - suffix)
                end = size - 1
            else:
                start = int(start_s)
                end = int(end_s) if end_s else size - 1
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            end = min(end, size - 1)
            status = 206

        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        if status == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        if head_only:
            return
        try:
            with path.open("rb") as handle:
                handle.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = handle.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _serve_static(self, url_path, head_only=False):
        candidate = self._safe_path(url_path)
        if candidate is None:
            self._send_json(403, {"ok": False, "error": "forbidden"})
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        if candidate == self.workbench_abs:
            self._serve_workbench(candidate, head_only)
        else:
            self._serve_file(candidate, head_only)

    # ---------- verbs ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path == "/api/health":
            self._send_json(200, {"ok": True, "service": "mv-keys", "pid": os.getpid()})
            return
        if path == "/api/keys":
            try:
                self._send_json(200, self._keys_status())
            except SystemExit:
                self._send_json(500, {"ok": False, "error": "读取 keys.json 失败"})
            except Exception:
                self._send_json(500, {"ok": False, "error": "读取配置失败"})
            return
        if path == "/api/balance":
            try:
                self._send_json(200, self._balance())
            except SystemExit:
                self._send_json(500, {"ok": False, "error": "读取 keys.json 失败"})
            except Exception:
                self._send_json(500, {"ok": False, "error": "余额查询失败"})
            return
        if path in ("/", "/go"):
            target = "/" + urllib.parse.quote(self.workbench_rel)
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._serve_static(path)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path in ("/", "/go"):
            target = "/" + urllib.parse.quote(self.workbench_rel)
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._serve_static(path, head_only=True)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path != "/api/keys":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        if not self._origin_ok():
            self._send_json(403, {"ok": False, "error": "origin not allowed"})
            return
        content_type = (self.headers.get("Content-Type") or "").lower()
        if "application/json" not in content_type:
            self._send_json(415, {"ok": False, "error": "Content-Type must be application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json(400, {"ok": False, "error": "empty body"})
            return
        if length > MAX_BODY:
            self._send_json(413, {"ok": False, "error": "body too large"})
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"ok": False, "error": "invalid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "error": "JSON body must be an object"})
            return
        try:
            status = self._update_keys(payload)
            self._send_json(200, status)
        except ValueError as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
        except SystemExit:
            self._send_json(500, {"ok": False, "error": "保存 keys.json 失败"})
        except Exception:
            self._send_json(500, {"ok": False, "error": "保存失败"})


def main():
    parser = argparse.ArgumentParser(description="MV 工作台本地 Key 配置服务（仅 127.0.0.1）")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="静态文件根目录（默认仓库根）")
    parser.add_argument(
        "--workbench",
        default="demo/workbench.html",
        help="workbench.html，相对 root 或绝对路径",
    )
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--timeout", type=int, default=12, help="余额查询超时秒数")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    workbench = Path(args.workbench).expanduser()
    if not workbench.is_absolute():
        workbench = (root / workbench).resolve()
    if not root.is_dir():
        print("静态根目录不存在：%s" % root, file=sys.stderr)
        return 1
    if not workbench.is_file():
        print("workbench 不存在：%s" % workbench, file=sys.stderr)
        return 1
    if root not in workbench.parents and workbench != root:
        print("workbench 必须在静态根目录内：%s" % workbench, file=sys.stderr)
        return 1

    Handler.root = root
    Handler.workbench_abs = workbench
    Handler.workbench_rel = workbench.relative_to(root).as_posix()
    Handler.balance_timeout = args.timeout

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print("端口 %d 启动失败：%s" % (args.port, exc), file=sys.stderr)
        return 1
    server.daemon_threads = True

    print("MV 工作台配置服务")
    print("  打开：http://127.0.0.1:%d/go" % args.port)
    print("  Key 文件：%s" % mv_keys.keys_path())
    print("  静态根目录：%s" % root)
    print("  Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
