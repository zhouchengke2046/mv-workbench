import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_server_api_and_injection(tmp_path):
    keys = tmp_path / "keys.json"
    port = free_port()
    env = os.environ.copy()
    env["MV_KEYS_PATH"] = str(keys)
    proc = subprocess.Popen([
        sys.executable, str(ROOT / "scripts" / "mv_keys_server.py"),
        "--root", str(ROOT), "--workbench", "demo/workbench.html",
        "--port", str(port), "--timeout", "5",
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = "http://127.0.0.1:%d" % port
        for _ in range(30):
            try:
                with urllib.request.urlopen(base + "/api/health", timeout=1) as resp:
                    assert resp.status == 200
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError("server did not start")

        with urllib.request.urlopen(base + "/api/keys", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        assert data["runninghub"]["configured"] is False

        payload = json.dumps({
            "runninghub": {"api_key": "rh-test-1234"},
            "router": {"api_key": "sk-test-5678"},
        }).encode()
        req = urllib.request.Request(
            base + "/api/keys", data=payload, method="POST",
            headers={"Content-Type": "application/json", "Origin": base},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        assert data["runninghub"]["masked"] == "••••1234"
        assert data["router"]["masked"] == "••••5678"

        bad = urllib.request.Request(
            base + "/api/keys", data=payload, method="POST",
            headers={"Content-Type": "application/json", "Origin": "https://evil.example"},
        )
        try:
            urllib.request.urlopen(bad, timeout=5)
            raise AssertionError("evil origin should be rejected")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403

        with urllib.request.urlopen(base + "/go", timeout=5) as resp:
            html = resp.read().decode()
        assert "MV_SERVER_MODE=true" in html
        assert "MV_KEY_UI" in html
        assert "配置 Key" in html
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
