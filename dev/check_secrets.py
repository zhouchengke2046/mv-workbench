#!/usr/bin/env python3
"""Fail if the repo contains obvious personal paths or real-looking API keys."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "docs", "out", "workspaces"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".html", ".txt", ".yml", ".yaml", ".sh", ".ps1", ".cmd"}
PATTERNS = [
    ("absolute home path", re.compile(r"/Users/[A-Za-z0-9_.-]+/")),
    ("github token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("long sk- key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("private key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("cn mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
]

def main():
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if "sk-YOUR" in line or "sk-xxx" in line or "test-key" in line or "fake" in line.lower():
                continue
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    hits.append("%s:%d: %s" % (path.relative_to(ROOT), lineno, label))
    if hits:
        print("potential secrets/personal paths:")
        print("\n".join(hits))
        return 1
    print("secret scan: clean")
    return 0

if __name__ == "__main__":
    sys.exit(main())
