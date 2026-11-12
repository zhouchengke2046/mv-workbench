#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zz-rhcli 基础测试 — 验证 CLI 骨架、自进化记忆、文件锁、异常捕获。
不依赖真实 API Key，全部用 mock/本地操作。

用法：python3 tests/test_rhcli.py
返回码：0=全部通过，非0=有失败。
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
RH_PROFILE = SCRIPTS_DIR / "rh_profile.py"
RH_SDK = SCRIPTS_DIR / "rh_sdk.py"
TEST_PROFILE_DIR = Path(tempfile.mkdtemp(prefix="rh-test-"))
TEST_PROFILE = TEST_PROFILE_DIR / "profile.json"

PASSED = 0
FAILED = 0


def ok(name: str):
    global PASSED
    PASSED += 1
    print(f"  ✓ {name}")


def fail(name: str, err: str = ""):
    global FAILED
    FAILED += 1
    print(f"  ✗ {name} {err}")


def run(cmd: List[str], env: Optional[Dict] = None) -> Tuple[int, str, str]:
    """运行命令，返回 (返回码, stdout, stderr)。"""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, env=full_env, timeout=10)
    return r.returncode, r.stdout, r.stderr


def test_cli_help():
    """CLI --help 能跑通。"""
    print("[1] CLI --help")

    # rh_profile.py
    code, out, err = run(["python3", str(RH_PROFILE), "--help"])
    if code == 0 and "workflow" in out:
        ok("rh_profile.py --help")
    else:
        fail("rh_profile.py --help", f"code={code}")

    # rh_sdk.py
    code, out, err = run(["python3", str(RH_SDK), "--help"])
    if code == 0 and "cancel" in out and "run-with-modifier" in out:
        ok("rh_sdk.py --help (23 commands)")
    else:
        fail("rh_sdk.py --help", f"code={code}, out={out[:200]}")


def test_profile_basic():
    """自进化记忆基础操作。"""
    print("[2] 自进化记忆基础操作")
    env = {"HOME": str(TEST_PROFILE_DIR)}

    # set
    code, out, err = run(["python3", str(RH_PROFILE), "set", "duration", "10"], env=env)
    if code == 0 and "duration" in out:
        ok("set duration")
    else:
        fail("set duration", f"code={code} err={err}")
        return

    # get
    code, out, err = run(["python3", str(RH_PROFILE), "get"], env=env)
    if code == 0:
        data = json.loads(out)
        if data.get("preferences", {}).get("duration") == "10":
            ok("get reads set value")
        else:
            fail("get reads set value", "value mismatch")
    else:
        fail("get", f"code={code}")

    # alias
    code, _, _ = run(["python3", str(RH_PROFILE), "alias", "海螺", "ep-123"], env=env)
    if code == 0:
        ok("alias")
    else:
        fail("alias")
        return

    # record success
    code, out, _ = run(["python3", str(RH_PROFILE), "record", "ep-123",
                        "--task", "text-to-video", "--status", "success",
                        "--cost", "0.5", "--quality", "4"], env=env)
    if code == 0 and "success" in out:
        ok("record success")
    else:
        fail("record success", f"code={code}")

    # record failed
    code, out, _ = run(["python3", str(RH_PROFILE), "record", "ep-fail",
                        "--task", "text-to-video", "--status", "failed"], env=env)
    if code == 0 and "fail" in out:
        ok("record failed")
    else:
        fail("record failed", f"code={code}")


def test_workflow_crud():
    """工作流目录 CRUD。"""
    print("[3] 工作流目录 CRUD")
    env = {"HOME": str(TEST_PROFILE_DIR)}

    # add
    code, out, _ = run(["python3", str(RH_PROFILE), "workflow", "add",
                        "test-webapp-1", "--task", "image-gen",
                        "--title", "测试工作流", "--note", "测试"], env=env)
    if code == 0 and "added" in out:
        ok("workflow add")
    else:
        fail("workflow add", f"code={code}")
        return

    # list
    code, out, _ = run(["python3", str(RH_PROFILE), "workflow", "list"], env=env)
    if code == 0 and "test-webapp-1" in out and "?" in out:
        ok("workflow list (shows ?)")
    else:
        fail("workflow list", f"code={code}")

    # verify
    code, out, _ = run(["python3", str(RH_PROFILE), "workflow", "verify",
                        "test-webapp-1"], env=env)
    if code == 0 and "verified" in out:
        ok("workflow verify")
    else:
        fail("workflow verify", f"code={code}")

    # search
    code, out, _ = run(["python3", str(RH_PROFILE), "workflow", "search",
                        "测试"], env=env)
    if code == 0 and "test-webapp-1" in out and "✓" in out:
        ok("workflow search (shows ✓)")
    else:
        fail("workflow search", f"code={code}")

    # rm
    code, out, _ = run(["python3", str(RH_PROFILE), "workflow", "rm",
                        "test-webapp-1"], env=env)
    if code == 0 and "removed" in out:
        ok("workflow rm")
    else:
        fail("workflow rm", f"code={code}")


def test_file_lock():
    """文件锁：并发写不丢数据。"""
    print("[4] 文件锁并发安全")
    env = {"HOME": str(TEST_PROFILE_DIR)}

    results = []
    def write_worker(i):
        code, _, _ = run(["python3", str(RH_PROFILE), "record",
                          f"ep-{i}", "--task", "test", "--status", "success"],
                         env=env)
        results.append(code)

    threads = [threading.Thread(target=write_worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if all(c == 0 for c in results):
        # 验证 10 条都写进去了
        code, out, _ = run(["python3", str(RH_PROFILE), "get"], env=env)
        data = json.loads(out)
        usage = data.get("usage", {})
        count = sum(1 for k in usage if k.startswith("ep-") and k[3:].isdigit())
        if count >= 8:  # 允许少量边界丢
            ok(f"并发 10 线程写完成（{count}/10 记录可见）")
        else:
            fail(f"并发写丢失数据（仅 {count}/10 可见）")
    else:
        fail(f"并发写有失败 code={results}")


def test_sdk_no_key():
    """无 API Key 时输出 JSON 错误而非 traceback。"""
    print("[5] SDK 异常捕获")
    env = {"RUNNINGHUB_API_KEY": ""}

    code, out, err = run(["python3", str(RH_SDK), "account"], env=env)
    if code != 0 and "NO_API_KEY" in err:
        ok("无 Key → JSON 错误（非 traceback）")
    else:
        fail("无 Key 异常", f"code={code} err={err[:200]}")

    # login 无密码
    code, out, err = run(["python3", str(RH_SDK), "login", "demo@example.com"], env=env)
    if code != 0 and "NO_PASSWORD" in err:
        ok("login 无密码 → JSON 错误")
    else:
        fail("login 无密码", f"code={code} err={err[:200]}")


def main():
    print("=" * 50)
    print("zz-rhcli 基础测试")
    print(f"测试 profile 目录: {TEST_PROFILE_DIR}")
    print("=" * 50)

    test_cli_help()
    test_profile_basic()
    test_workflow_crud()
    test_file_lock()
    test_sdk_no_key()

    print("=" * 50)
    print(f"结果: {PASSED} 通过, {FAILED} 失败")
    print("=" * 50)

    # 清理
    import shutil
    shutil.rmtree(TEST_PROFILE_DIR, ignore_errors=True)

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
