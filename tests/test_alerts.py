import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import alerts  # noqa: E402
import mv_keys  # noqa: E402


def test_emit_format_and_redaction(capsys):
    secret = "rh-super-secret-key"
    text = alerts.emit(
        "B001",
        platform="router", model="muse-video-ext", error_class="timeout",
        stats="连续失败=3/10min", checks="keys status ✓",
        raw="URLError: operation timed out; key=" + secret, secrets=[secret],
        stream=sys.stdout,
    )
    out = capsys.readouterr().out
    assert out.strip() == text.strip()
    assert "[提醒] B001 Router 连续失败，备用 Key 未配置" in out
    assert "级别=阻塞" in out and "平台=router" in out
    assert "学生动作" in out and "需要老师" in out
    assert secret not in out and "***" in out


def test_emit_truncates_raw(capsys):
    alerts.emit("P3", raw="x" * 500, stream=sys.stdout)
    out = capsys.readouterr().out
    assert "…" in out
    assert "xxxxxx" * 60 not in out


def test_unknown_code():
    with pytest.raises(ValueError):
        alerts.emit("NOPE", stream=sys.stdout)


def test_mv_keys_die_with_alert(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MV_KEYS_PATH", str(tmp_path / "keys.json"))
    with pytest.raises(SystemExit):
        mv_keys.die("这条命令需要 router key", alert="K001", platform="router")
    err = capsys.readouterr().err
    assert "[提醒] K001 Key 未配置" in err
    assert "平台=router" in err
    data = json.loads(err.strip().splitlines()[-1])
    assert data["ok"] is False
