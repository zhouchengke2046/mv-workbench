import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    result = (resp.status, dict(resp.getheaders()), data)
    conn.close()
    return result


def test_server_api_and_injection(tmp_path):
    keys = tmp_path / "keys.json"
    port = free_port()
    env = os.environ.copy()
    env["MV_KEYS_PATH"] = str(keys)
    proc = subprocess.Popen([
        sys.executable, str(ROOT / "scripts" / "mv_keys_server.py"),
        "--root", str(ROOT), "--workbench", "demo/workbench.html",
        "--port", str(port), "--timeout", "5",
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(40):
            if proc.poll() is not None:
                err = proc.stderr.read().decode("utf-8", "replace")
                raise AssertionError("server exited: " + err[-1200:])
            try:
                status, _, _ = request(port, "GET", "/api/health")
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("server did not start")

        status, _, body = request(port, "GET", "/api/health")
        assert status == 200
        health = json.loads(body.decode())
        assert health["workbench"] == "demo/workbench.html"

        status, _, body = request(port, "GET", "/api/keys")
        assert status == 200
        data = json.loads(body.decode())
        assert data["runninghub"]["configured"] is False

        payload = json.dumps({
            "runninghub": {"api_key": "rh-test-1234"},
            "router": {"api_key": "sk-test-5678"},
        }).encode()
        status, _, body = request(
            port, "POST", "/api/keys", body=payload,
            headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % port},
        )
        assert status == 200, body.decode("utf-8", "replace")
        data = json.loads(body.decode())
        assert data["runninghub"]["masked"] == "••••1234"
        assert data["router"]["masked"] == "••••5678"

        status, _, _ = request(
            port, "POST", "/api/keys", body=payload,
            headers={"Content-Type": "application/json", "Origin": "https://evil.example"},
        )
        assert status == 403

        status, _, body = request(port, "GET", "/demo/workbench.html")
        assert status == 200
        html = body.decode()
        assert "MV_SERVER_MODE=true" in html
        assert "MV_KEY_UI" in html
        assert "配置 Key" in html
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
