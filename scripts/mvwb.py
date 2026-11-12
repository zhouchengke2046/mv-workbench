#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV Workbench CLI.

Usage:
  mvwb doctor [--network]
  mvwb open [--workspace NAME] [--port 8776] [--no-open]
  mvwb server [--workspace NAME] [--port 8776]
  mvwb status [--port 8776]
  mvwb keys [status|set|config|balance ...]
  mvwb quote [--model muse-video-ext] [--seconds 2] [--images 1] [--segments 1]
  mvwb init <name>
  mvwb build --data demo/data.json --out demo/workbench.html
"""
import argparse
import http.client
import json
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DEMO = ROOT / "demo"
KEYS_SCRIPT = SCRIPTS / "mv_keys.py"
SERVER_SCRIPT = SCRIPTS / "mv_keys_server.py"
BUILD_SCRIPT = SCRIPTS / "build_workbench.py"
CONFIG = ROOT / "config" / "models.json"

sys.path.insert(0, str(SCRIPTS))
import mv_keys  # noqa: E402
from console import setup  # noqa: E402
setup()

OK = "[ok]"
WARN = "[warn]"
FAIL = "[fail]"


def run(cmd):
    return subprocess.call([sys.executable] + cmd)


def cmd_doctor(args):
    failures = 0
    print("MV Workbench doctor")
    print("=" * 48)

    v = sys.version_info
    if v >= (3, 9):
        print("%s Python %d.%d.%d" % (OK, v.major, v.minor, v.micro))
    else:
        print("%s Python %d.%d.%d（需要 3.9+）" % (FAIL, v.major, v.minor, v.micro))
        failures += 1

    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if path:
            print("%s %s: %s" % (OK, tool, path))
        else:
            print("%s %s 未找到（时间轴/时长检查需要）" % (WARN, tool))

    if (DEMO / "workbench.html").is_file():
        print("%s demo/workbench.html" % OK)
    else:
        print("%s demo/workbench.html 缺失" % FAIL)
        failures += 1

    service = _find_service(8776)
    if service:
        print("%s 服务版运行: http://127.0.0.1:%d/go（%s）" % (OK, service["port"], service.get("workbench") or "未知工作台"))
    else:
        print("%s 服务版未运行；配置 Key 用 mvwb open" % WARN)

    required = [
        "SKILL.md",
        "scripts/mvwb.py",
        "scripts/mv_keys.py",
        "scripts/providers/runninghub.py",
        "scripts/providers/tokentech_video.py",
        "references/workbench-contract.md",
        "templates/workbench.html",
        "demo/workbench.html",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        print("%s 缺少文件: %s" % (FAIL, ", ".join(missing)))
        failures += 1
    else:
        print("%s 单 skill 文件齐备" % OK)

    try:
        cfg, exists = mv_keys.load_cfg()
        rh = (cfg.get("runninghub") or {}).get("api_key") or ""
        rt = (cfg.get("router") or {}).get("api_key") or ""
        print("%s keys.json: %s" % (OK if exists else WARN, mv_keys.keys_path()))
        print("  RunningHub: %s" % ("已配置 " + mv_keys.mask(rh) if rh else "未配置"))
        print("  Router:     %s" % ("已配置 " + mv_keys.mask(rt) if rt else "未配置"))
        if not rh and not rt:
            print("%s 还没配 Key；运行 mvwb open，在页面右上角“配置 Key”" % WARN)
    except SystemExit:
        print("%s keys.json 读取失败" % FAIL)
        failures += 1

    if args.network:
        print("-" * 48)
        try:
            cfg, _ = mv_keys.load_cfg()
            payload = {
                "checked_at": mv_keys.now_iso(),
                "runninghub": mv_keys.balance_runninghub(cfg, 10),
                "router": mv_keys.balance_router(cfg, 10),
            }
            for name in ("runninghub", "router"):
                item = payload[name]
                if item.get("configured") and item.get("ok"):
                    print("%s %s 余额: %s %s" % (OK, name, item.get("balance"), item.get("unit")))
                else:
                    print("%s %s: %s" % (WARN, name, item.get("error")))
        except SystemExit:
            print("%s 余额查询失败" % WARN)

    print("=" * 48)
    if failures:
        print("有 %d 个阻塞项，先修复再继续。" % failures)
        return 1
    print("环境可用。下一步：mvwb open  （打开服务版工作台）")
    return 0


def _service_info(port):
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.25)
        conn.request("GET", "/api/health")
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        if resp.status != 200:
            return None
        data = json.loads(body.decode("utf-8"))
        if data.get("service") != "mv-keys":
            return None
        data["port"] = port
        return data
    except Exception:
        return None


def _service_ok(port):
    return _service_info(port) is not None


def _find_service(start=8776, count=5):
    fallback = None
    for port in range(start, start + count):
        info = _service_info(port)
        if info:
            if info.get("workbench"):
                return info
            fallback = fallback or info
    return fallback


def _port_free(port):
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _choose_port(preferred):
    for port in range(preferred, preferred + 20):
        if _port_free(port):
            return port
    raise SystemExit("没有可用端口：%d-%d" % (preferred, preferred + 19))


def _workbench_path(args):
    if getattr(args, "workspace", None):
        candidate = ROOT / "workspaces" / args.workspace / "workbench.html"
    elif getattr(args, "workbench", None):
        candidate = Path(args.workbench).expanduser()
        if not candidate.is_absolute():
            candidate = ROOT / candidate
    else:
        candidate = DEMO / "workbench.html"
    candidate = candidate.resolve()
    if ROOT not in candidate.parents and candidate != ROOT:
        raise SystemExit("workbench 必须在仓库目录内：%s" % candidate)
    if not candidate.is_file():
        raise SystemExit("找不到 workbench：%s" % candidate)
    return candidate


def cmd_server(args):
    workbench = _workbench_path(args)
    rel = workbench.relative_to(ROOT).as_posix()
    port = args.port
    cmd = [
        str(SERVER_SCRIPT),
        "--root", str(ROOT),
        "--workbench", rel,
        "--port", str(port),
        "--timeout", str(args.timeout),
    ]
    if args.open:
        url = "http://127.0.0.1:%d/go" % port
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print("工作台：http://127.0.0.1:%d/go" % port)
    print("Key 配置：页面右上角“配置 Key”")
    return run(cmd)


def cmd_demo(args):
    args.workspace = None
    args.workbench = None
    args.open = True
    return cmd_open(args)


def cmd_open(args):
    preferred = args.port
    open_browser = getattr(args, "open", True)
    desired = _workbench_path(args).relative_to(ROOT).as_posix()
    info = _service_info(preferred)
    if info and info.get("workbench") == desired:
        url = "http://127.0.0.1:%d/go" % preferred
        print("服务版已在运行：%s" % url)
        if open_browser:
            webbrowser.open(url)
        return 0
    if info:
        print("端口 %d 是另一个工作台（%s），不会复用" % (preferred, info.get("workbench") or "未知"))
    port = preferred if _port_free(preferred) else _choose_port(preferred + 1)
    if port != preferred:
        print("端口 %d 被占用，改用 %d" % (preferred, port))
    args.port = port
    args.open = open_browser
    return cmd_server(args)


def cmd_status(args):
    info = _service_info(args.port) or _find_service(args.port, 5)
    if info:
        print(json.dumps({
            "running": True,
            "url": "http://127.0.0.1:%d/go" % info["port"],
            "port": info["port"],
            "workbench": info.get("workbench") or "",
        }, ensure_ascii=False))
        return 0
    print(json.dumps({"running": False, "hint": "运行 mvwb open 启动服务版"}, ensure_ascii=False))
    return 1


def cmd_rh(args):
    script = SCRIPTS / "providers" / "runninghub.py"
    if not script.is_file():
        raise SystemExit("缺少 %s" % script)
    return subprocess.call([
        sys.executable, str(KEYS_SCRIPT), "exec", "--need", "runninghub", "--",
        sys.executable, str(script)
    ] + list(args.args or []))


def cmd_timeline(args):
    script = SCRIPTS / "timeline.py"
    if not script.is_file():
        raise SystemExit("缺少 %s" % script)
    return subprocess.call([sys.executable, str(script)] + list(args.args or []))


def cmd_muse(args):
    script = SCRIPTS / "providers" / "tokentech_video.py"
    if not script.is_file():
        raise SystemExit("缺少 %s" % script)
    return subprocess.call([
        sys.executable, str(KEYS_SCRIPT), "exec", "--need", "router", "--",
        sys.executable, str(script)
    ] + list(args.args or []))


def cmd_keys(args):
    rest = list(args.args or [])
    if not rest:
        rest = ["status"]
    return run([str(KEYS_SCRIPT)] + rest)


def cmd_quote(args):
    if not CONFIG.is_file():
        raise SystemExit("缺少 config/models.json")
    models = json.loads(CONFIG.read_text(encoding="utf-8")).get("models", {})
    model = args.model
    if model not in models:
        raise SystemExit("未知模型：%s（可选：%s）" % (model, ", ".join(sorted(models))))
    spec = models[model]
    unit = spec.get("unit", "")
    if "price_per_second" in spec:
        total = float(spec["price_per_second"]) * args.seconds
        detail = "%ss × %s %s/s" % (args.seconds, spec["price_per_second"], unit)
    elif "price_per_4s" in spec:
        total = float(spec["price_per_4s"]) * args.segments * max(1.0, args.seconds / 4.0)
        detail = "%d 段 × %.1fs（按 4s 单价折算）" % (args.segments, args.seconds)
    elif "price_per_8s" in spec:
        total = float(spec["price_per_8s"]) * args.segments * max(1.0, args.seconds / 8.0)
        detail = "%d 段 × %.1fs（按 8s 单价折算）" % (args.segments, args.seconds)
    elif "price_per_image" in spec:
        total = float(spec["price_per_image"]) * args.images
        detail = "%d 张 × %s %s/张" % (args.images, spec["price_per_image"], unit)
    elif "price" in spec:
        total = float(spec["price"]) * max(1, args.segments)
        detail = "%d 次 × %s %s" % (max(1, args.segments), spec["price"], unit)
    else:
        raise SystemExit("模型 %s 没有价格字段" % model)
    print("%s" % model)
    print("  计费：%s" % detail)
    print("  估算：%.2f %s" % (total, unit))
    print("  以服务商实际账单为准（as_of %s）" % json.loads(CONFIG.read_text(encoding="utf-8")).get("as_of", "?"))
    return 0


def cmd_init(args):
    name = args.name.strip()
    if not name or "/" in name or "\\" in name:
        raise SystemExit("名字不合法")
    target = ROOT / "workspaces" / name
    if target.exists():
        raise SystemExit("已存在：%s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DEMO, target)
    print("已创建：%s" % target)
    print("下一步：替换 %s/原文/ 里的歌词和脚本，然后用 agent 按四步生成。" % target.name)
    return 0


def cmd_build(args):
    return run([
        str(BUILD_SCRIPT),
        "--template", str(ROOT / args.template),
        "--data", str(Path(args.data).expanduser()),
        "--out", str(Path(args.out).expanduser()),
    ])


def build_parser():
    p = argparse.ArgumentParser(prog="mvwb", description="MV Workbench CLI")
    sub = p.add_subparsers(dest="cmd")

    doctor = sub.add_parser("doctor", help="检查环境/依赖/Key")
    doctor.add_argument("--network", action="store_true", help="同时查询余额（需要 Key）")

    server = sub.add_parser("server", help="启动本地工作台")
    server.add_argument("--workspace", help="workspaces/<name>")
    server.add_argument("--workbench", help="repo 内的 workbench.html 路径")
    server.add_argument("--port", type=int, default=8776)
    server.add_argument("--timeout", type=int, default=12)
    server.add_argument("--no-open", dest="open", action="store_false", help="不自动打开浏览器")
    server.set_defaults(open=True)

    sub.add_parser("demo", help="启动 demo 工作台并打开浏览器")

    rh = sub.add_parser("rh", help="RunningHub 生成（透传 rh_run.py 参数）", add_help=False)
    rh.add_argument("args", nargs=argparse.REMAINDER)

    muse = sub.add_parser("muse", help="Muse 生成（Router /v1/videos）", add_help=False)
    muse.add_argument("args", nargs=argparse.REMAINDER)

    timeline = sub.add_parser("timeline", help="生成/对齐音乐时间轴（透传 timeline.py）", add_help=False)
    timeline.add_argument("args", nargs=argparse.REMAINDER)

    open_cmd = sub.add_parser("open", help="启动/复用服务版并打开工作台")
    open_cmd.add_argument("--workspace", help="workspaces/<name>")
    open_cmd.add_argument("--workbench", help="repo 内的 workbench.html 路径")
    open_cmd.add_argument("--port", type=int, default=8776)
    open_cmd.add_argument("--timeout", type=int, default=12)
    open_cmd.add_argument("--no-open", dest="open", action="store_false", help="不自动打开浏览器")
    open_cmd.set_defaults(open=True)

    status = sub.add_parser("status", help="查看服务版是否运行")
    status.add_argument("--port", type=int, default=8776)

    keys = sub.add_parser("keys", help="Key 管理（status/set/config/balance）", add_help=False)
    keys.add_argument("args", nargs=argparse.REMAINDER)

    quote = sub.add_parser("quote", help="按 config/models.json 估算费用")
    quote.add_argument("--model", default="muse-video-ext")
    quote.add_argument("--seconds", type=float, default=2)
    quote.add_argument("--images", type=int, default=1)
    quote.add_argument("--segments", type=int, default=1)

    init = sub.add_parser("init", help="从 demo 创建 workspaces/<name>")
    init.add_argument("name")

    build = sub.add_parser("build", help="用 DATA 构建 workbench.html")
    build.add_argument("--template", default="templates/workbench.html")
    build.add_argument("--data", default="demo/data.json")
    build.add_argument("--out", default="demo/workbench.html")
    return p


def main():
    parser = build_parser()
    args, extras = parser.parse_known_args()
    if args.cmd in ("rh", "muse", "timeline", "keys"):
        args.args = list(getattr(args, "args", []) or []) + list(extras)
    elif extras:
        parser.error("unrecognized arguments: " + " ".join(extras))
    if not args.cmd:
        parser.print_help()
        return 0
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "server":
        return cmd_server(args)
    if args.cmd == "demo":
        return cmd_demo(args)
    if args.cmd == "open":
        return cmd_open(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "rh":
        return cmd_rh(args)
    if args.cmd == "timeline":
        return cmd_timeline(args)
    if args.cmd == "muse":
        return cmd_muse(args)
    if args.cmd == "keys":
        return cmd_keys(args)
    if args.cmd == "quote":
        return cmd_quote(args)
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "build":
        return cmd_build(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
