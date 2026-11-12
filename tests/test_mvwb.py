import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mvwb  # noqa: E402


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_port_free():
    port = free_port()
    assert mvwb._port_free(port) is True


def test_service_info_none():
    port = free_port()
    assert mvwb._service_info(port) is None


def test_status_reports_not_running():
    port = free_port()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mvwb.py"), "status", "--port", str(port)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=os.environ.copy(), timeout=10,
    )
    assert proc.returncode == 1
    assert '"running": false' in proc.stdout
