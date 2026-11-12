#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流注册表测试：JSON 合法性、路由、查询、渲染。

用法：python3 tests/test_registry.py
返回码：0=全部通过，非0=有失败。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "rh_registry.py"
DATA = SKILL_DIR / "references" / "workflows.json"
RENDERED = SKILL_DIR / "references" / "workflows.md"

PASSED = 0
FAILED = 0


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def ok(name: str):
    global PASSED
    PASSED += 1
    print(f"  ✓ {name}")


def fail(name: str, detail: str = ""):
    global FAILED
    FAILED += 1
    print(f"  ✗ {name} {detail}")


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        ok(name)
    else:
        fail(name, detail)


def main() -> int:
    print("[1] JSON 与校验")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    check("JSON 可解析", isinstance(data.get("workflows"), list))
    check("登记项 >= 40", len(data["workflows"]) >= 40, f"实际 {len(data['workflows'])}")
    r = run("validate")
    check("validate 通过", r.returncode == 0, r.stdout + r.stderr)

    print("[2] 路由")
    r = run("route", "我要把视频里的主播批量换人")
    check("批量换人 → 2099805997966643202", "2099805997966643202" in r.stdout, r.stdout)
    r = run("route", "给短剧出一段口播视频")
    check("口播视频 → 2110943749894402050", "2110943749894402050" in r.stdout, r.stdout)
    r = run("route", "Qwen3 TTS 旁白")
    check("Qwen3 → 2086427153989726210", "2086427153989726210" in r.stdout, r.stdout)

    print("[3] 查询")
    r = run("show", "终极篇")
    check("show 别名", r.returncode == 0 and "2110943749894402050" in r.stdout, r.stdout)
    r = run("find", "MOSS")
    check("find MOSS", r.returncode == 0 and "2116462203997081601" in r.stdout, r.stdout)
    r = run("list", "--all", "--json")
    check("list --all --json", r.returncode == 0 and json.loads(r.stdout), r.stdout[:200])

    print("[4] 渲染")
    r = run("render")
    check("render 成功", r.returncode == 0, r.stdout + r.stderr)
    text = RENDERED.read_text(encoding="utf-8")
    for ident in ("2110943749894402050", "2101142038568849410", "2116462203997081601", "2099805997966643202"):
        check(f"workflows.md 含 {ident}", ident in text)

    print(f"\n{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
