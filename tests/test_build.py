import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_build_demo(tmp_path):
    out = tmp_path / "workbench.html"
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "build_workbench.py"),
        "--template", str(ROOT / "templates" / "workbench.html"),
        "--data", str(ROOT / "demo" / "data.json"),
        "--out", str(out),
    ], check=True)
    html = out.read_text(encoding="utf-8")
    i = html.index("const DATA = ") + len("const DATA = ")
    data, _ = json.JSONDecoder().raw_decode(html[i:])
    assert data["meta"]["title"] == "末班地铁"
    assert len(data["mvs"]) == 3
    assert '"api_key": "' not in html.replace('"api_key": ""', "")
