import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mv_keys  # noqa: E402


def test_mask():
    assert mv_keys.mask("") == ""
    assert mv_keys.mask("sk-1234567890") == "••••7890"


def test_save_and_load(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    monkeypatch.setenv("MV_KEYS_PATH", str(path))
    cfg = json.loads(json.dumps(mv_keys.TEMPLATE))
    cfg["runninghub"]["api_key"] = "rh-test-1234"
    cfg["router"]["api_key"] = "router-test-5678"
    mv_keys.save_cfg(cfg)
    loaded, exists = mv_keys.load_cfg()
    assert exists
    assert loaded["runninghub"]["api_key"] == "rh-test-1234"
    if os.name != "nt":
        assert (path.stat().st_mode & 0o777) == 0o600


def test_newapi_balance(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, payload):
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/api/status":
                self._send({"data": {"quota_display_type": "CNY"}})
            elif self.path == "/v1/dashboard/billing/subscription":
                self._send({"hard_limit_usd": 73.0})
            elif self.path == "/v1/dashboard/billing/usage":
                self._send({"total_usage": 3650})
            else:
                self._send({"error": "not found"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cfg = json.loads(json.dumps(mv_keys.TEMPLATE))
        cfg["router"].update({
            "api_key": "test-key",
            "base_url": "http://127.0.0.1:%d" % server.server_port,
            "balance_mode": "newapi",
            "proxy": "",
        })
        result = mv_keys.balance_router(cfg, 5)
        assert result["ok"] is True
        assert result["balance"] == 36.5
        assert result["unit"] == "CNY"
    finally:
        server.shutdown()


def test_update_data_keys(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"meta": {"id": "D01"}, "mvs": []}), encoding="utf-8")
    keys_data = {
        "runninghub": {"configured": True, "masked": "••••1234", "balance": 100, "unit": "币"},
        "router": {"configured": True, "masked": "••••5678", "balance": 20.0, "unit": "CNY"},
    }
    mv_keys.update_data_keys(str(data_path), keys_data)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert data["meta"]["id"] == "D01"
    assert data["keys"]["runninghub"]["balance"] == 100
    raw = data_path.read_text(encoding="utf-8")
    assert "sk-test" not in raw and "rh-test" not in raw


def test_import_keys_and_delete_source(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MV_KEYS_PATH", str(tmp_path / "keys.json"))
    src = tmp_path / "mv-keys-import.json"
    src.write_text(json.dumps({
        "mv_keys_import": 1,
        "runninghub": {"api_key": "rh-import-1234"},
        "router": {"api_key": "sk-import-5678"},
    }), encoding="utf-8")
    args = type("A", (), {"file": str(src), "delete_source": True})()
    mv_keys.cmd_import(args)
    out = capsys.readouterr().out
    assert "••••1234" in out and "••••5678" in out
    assert not src.exists()
    cfg, _ = mv_keys.load_cfg()
    assert cfg["runninghub"]["api_key"] == "rh-import-1234"
    assert cfg["router"]["api_key"] == "sk-import-5678"


def test_set_refuses_without_tty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MV_KEYS_PATH", str(tmp_path / "keys.json"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    args = type("A", (), {
        "name": "runninghub", "stdin": False, "label": None, "account": None,
        "base_url": None, "balance_path": None, "balance_mode": None,
        "provider": None, "proxy": None,
    })()
    with pytest.raises(SystemExit):
        mv_keys.cmd_set(args)
    assert "没有可交互终端" in capsys.readouterr().err


def test_exec_clears_stale_env(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    monkeypatch.setenv("MV_KEYS_PATH", str(path))
    cfg = json.loads(json.dumps(mv_keys.TEMPLATE))
    cfg["runninghub"]["api_key"] = "rh-good"
    cfg["router"]["api_key"] = "router-good"
    mv_keys.save_cfg(cfg)
    env = os.environ.copy()
    env["MV_KEYS_PATH"] = str(path)
    env["RUNNINGHUB_API_KEY"] = "wrong"
    env["ROUTER_API_KEY"] = "wrong"
    code = "import os; print(os.environ.get('RUNNINGHUB_API_KEY')); print(os.environ.get('ROUTER_API_KEY')); print(os.environ.get('APIMART_KEY'))"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mv_keys.py"), "exec", "--need", "runninghub", "--",
         sys.executable, "-c", code],
        env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.strip().splitlines()
    assert lines[0] == "rh-good"
    assert lines[1] == "router-good"
    assert lines[2] == "router-good"
