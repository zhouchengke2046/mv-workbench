#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build workbench.html from a template + DATA JSON.

The template keeps CSS/JS; only `const DATA = ...;` is replaced.
"""
import argparse
import json
import sys
from pathlib import Path

from console import setup

setup()

MARKER = "const DATA = "


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="templates/workbench.html")
    parser.add_argument("--data", default="demo/data.json")
    parser.add_argument("--out", default="demo/workbench.html")
    args = parser.parse_args()

    template = Path(args.template).expanduser()
    data_path = Path(args.data).expanduser()
    out = Path(args.out).expanduser()
    if not template.is_file():
        raise SystemExit("template not found: %s" % template)
    if not data_path.is_file():
        raise SystemExit("data not found: %s" % data_path)

    html = template.read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(k in data for k in ("meta", "lyric", "script", "mvs")):
        raise SystemExit("DATA must contain meta/lyric/script/mvs")
    if "keys" not in data:
        data["keys"] = {}

    serialized = json.dumps(data, ensure_ascii=False)
    # Never allow raw secrets in a generated page.
    for section in ("runninghub", "router"):
        key = ((data.get("keys") or {}).get(section) or {}).get("api_key")
        if key:
            raise SystemExit("refusing to build: DATA.keys.%s contains a raw api_key" % section)

    index = html.find(MARKER)
    if index < 0:
        raise SystemExit("template missing %r" % MARKER)
    start = index + len(MARKER)
    try:
        _, end = json.JSONDecoder().raw_decode(html[start:])
    except json.JSONDecodeError as exc:
        raise SystemExit("template DATA is not valid JSON: %s" % exc)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html[:start] + serialized + html[start + end:], encoding="utf-8")
    print("built %s (%d bytes)" % (out, out.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
