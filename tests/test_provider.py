import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(BaseHTTPRequestHandler):
    payload = None

    def log_message(self, *args):
        pass

    def _send(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        Handler.payload = json.loads(self.rfile.read(length).decode())
        self._send(200, json.dumps({"id": "task_test", "status": "queued"}).encode())

    def do_GET(self):
        if self.path == "/v1/videos/task_test":
            self._send(200, json.dumps({"id": "task_test", "status": "completed"}).encode())
        elif self.path == "/v1/videos/task_test/content":
            self._send(200, b"fake-video-bytes", "video/mp4")
        else:
            self._send(404, b"{}")


def test_adapter(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    keys = tmp_path / "keys.json"
    keys.write_text(json.dumps({
        "runninghub": {"api_key": ""},
        "router": {
            "api_key": "test-key",
            "base_url": "http://127.0.0.1:%d" % server.server_port,
            "balance_mode": "newapi",
            "proxy": "",
        },
    }), encoding="utf-8")
    env = os.environ.copy()
    env["MV_KEYS_PATH"] = str(keys)
    env["ROUTER_API_KEY"] = "test-key"
    out = tmp_path / "out.mp4"
    try:
        proc = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "providers" / "tokentech_video.py"),
            "--prompt", "test", "--seconds", "2", "--size", "720x1280",
            "--out", str(out), "--poll-interval", "0", "--poll-limit", "3",
        ], env=env, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert out.read_bytes() == b"fake-video-bytes"
        assert Handler.payload["seconds"] == 2
        assert Handler.payload["size"] == "720x1280"
        assert Handler.payload["model"] == "muse-video-ext"
    finally:
        server.shutdown()
