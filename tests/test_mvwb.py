import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mvwb  # noqa: E402


def test_workbench_path_defaults_to_demo():
    args = type("A", (), {"workspace": None, "workbench": None})()
    assert mvwb._workbench_path(args) == (ROOT / "demo" / "workbench.html").resolve()


def test_open_uses_file_uri(monkeypatch, tmp_path, capsys):
    page = tmp_path / "workbench.html"
    page.write_text("<html></html>", encoding="utf-8")
    seen = {}
    monkeypatch.setattr(mvwb.webbrowser, "open", lambda uri: seen.setdefault("uri", uri))
    args = type("A", (), {"workspace": None, "workbench": str(page), "open": True})()
    assert mvwb.cmd_open(args) == 0
    assert seen["uri"] == page.resolve().as_uri()
    assert "静态文件" in capsys.readouterr().out


def test_passthrough_keeps_option_values(monkeypatch):
    seen = {}

    def fake_muse(args):
        seen["args"] = list(args.args)
        return 0

    monkeypatch.setattr(mvwb, "cmd_muse", fake_muse)
    monkeypatch.setattr(sys, "argv", [
        "mvwb", "muse", "--prompt", "test shot", "--seconds", "2", "--out", "x.mp4",
    ])
    assert mvwb.main() == 0
    assert seen["args"] == ["--prompt", "test shot", "--seconds", "2", "--out", "x.mp4"]


def test_check_reports_missing_refs(tmp_path, capsys):
    (tmp_path / "ok.png").write_bytes(b"x")
    data = {
        "mvs": [{"detail": {
            "assets": [{"url": "ok.png"}, {"url": "missing.png"}],
            "music": [{"audio": "ok.mp3"}],
        }}],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(data), encoding="utf-8")
    args = type("A", (), {"data": str(data_path), "workbench": None})()
    assert mvwb.cmd_check(args) == 1
    out = capsys.readouterr().out
    assert "missing.png" in out
    assert "缺失/空文件：2" in out


def test_init_creates_empty_project():
    name = "pytest_empty_%d" % os.getpid()
    target = ROOT / "workspaces" / name
    if target.exists():
        shutil.rmtree(target)
    try:
        args = type("A", (), {"name": name, "demo": False})()
        assert mvwb.cmd_init(args) == 0
        data = json.loads((target / "data.json").read_text(encoding="utf-8"))
        assert data["mvs"] == []
        assert not (target / "MV001").exists()
        assert (target / "workbench.html").is_file()
        assert (target / "原文" / "lyric_original.md").read_text(encoding="utf-8") == ""
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_init_demo_flag_copies_demo():
    name = "pytest_demo_%d" % os.getpid()
    target = ROOT / "workspaces" / name
    if target.exists():
        shutil.rmtree(target)
    try:
        args = type("A", (), {"name": name, "demo": True})()
        assert mvwb.cmd_init(args) == 0
        data = json.loads((target / "data.json").read_text(encoding="utf-8"))
        assert data["mvs"]
        assert (target / "MV001").is_dir()
    finally:
        shutil.rmtree(target, ignore_errors=True)


def test_resolve_input_falls_back_to_skill_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert mvwb._resolve_input("demo/data.json") == (ROOT / "demo" / "data.json").resolve()


def test_resolve_output_uses_skill_root_when_cwd_parent_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert mvwb._resolve_output("templates/out.html") == (ROOT / "templates" / "out.html").resolve()
