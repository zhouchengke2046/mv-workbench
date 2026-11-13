#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV Workbench CLI.

Usage:
  mvwb doctor [--network]
  mvwb open [--workspace NAME] [--workbench PATH] [--no-open]
  mvwb demo
  mvwb keys [status|set|config|balance ...]
  mvwb quote [--model muse-video-ext] [--seconds 2] [--images 1] [--segments 1]
  mvwb check [--data demo/data.json] [--workbench PATH]
  mvwb init <name>
  mvwb build --data demo/data.json --out demo/workbench.html
"""
import argparse
import json
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DEMO = ROOT / "demo"
KEYS_SCRIPT = SCRIPTS / "mv_keys.py"
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

    print("%s 工作台是静态文件，直接用浏览器打开；不需要后台服务" % OK)

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
            print("%s 还没配 Key；运行 mvwb keys set runninghub / router（输入不回显）" % WARN)
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
    print("环境可用。下一步：mvwb open  （用浏览器打开静态工作台）")
    return 0


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
    if not candidate.is_file():
        raise SystemExit("找不到 workbench：%s" % candidate)
    return candidate


def cmd_demo(args):
    args.workspace = None
    args.workbench = None
    args.open = True
    return cmd_open(args)


def cmd_open(args):
    """静态工作台：只打开本地 HTML，不启动任何服务。"""
    workbench = _workbench_path(args)
    print("工作台：%s" % workbench)
    print("这是静态文件；Key/余额由 agent 用 mvwb keys 更新后重新 build。")
    if getattr(args, "open", True):
        webbrowser.open(workbench.as_uri())
    return 0


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


REF_KEYS = {"url", "audio", "poster", "file", "video_file", "src"}


def _collect_refs(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in REF_KEYS and isinstance(value, str) and value.strip():
                out.append(value.strip())
            else:
                _collect_refs(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, out)


def cmd_check(args):
    data_path = Path(args.data).expanduser().resolve()
    if not data_path.is_file():
        raise SystemExit("找不到 DATA：%s" % data_path)
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SystemExit("DATA 不是合法 JSON：%s（%s）" % (data_path, exc))

    refs = []
    _collect_refs(payload, refs)
    base = data_path.parent
    missing, seen = [], set()
    for ref in refs:
        if ref.startswith(("http://", "https://", "data:", "blob:")) or ref in seen:
            continue
        seen.add(ref)
        target = (base / ref).resolve()
        if not target.is_file() or target.stat().st_size <= 0:
            missing.append(ref)

    print("DATA：%s" % data_path)
    print("本地引用：%d 个，缺失/空文件：%d 个" % (len(seen), len(missing)))
    for ref in missing:
        print("  [missing] %s" % ref)

    wb = Path(args.workbench).expanduser() if args.workbench else base / "workbench.html"
    if not wb.is_absolute():
        wb = (Path.cwd() / wb).resolve()
    if wb.is_file() and data_path.stat().st_mtime > wb.stat().st_mtime:
        print("[warn] DATA 比 %s 新，页面还是旧的：先运行 mvwb build" % wb.name)
    elif not wb.is_file():
        print("[warn] 同目录没有 workbench.html；生成后运行 mvwb build")

    if missing:
        print("[fail] 有 %d 个本地文件找不到；视频/资产不会显示在工作台" % len(missing))
        return 1
    print("[ok] DATA 里的本地资产/视频都存在")
    return 0


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

    sub.add_parser("demo", help="用浏览器打开 demo 工作台")

    rh = sub.add_parser("rh", help="RunningHub 生成（透传 rh_run.py 参数）", add_help=False)
    rh.add_argument("args", nargs=argparse.REMAINDER)

    muse = sub.add_parser("muse", help="Muse 生成（Router /v1/videos）", add_help=False)
    muse.add_argument("args", nargs=argparse.REMAINDER)

    timeline = sub.add_parser("timeline", help="生成/对齐音乐时间轴（透传 timeline.py）", add_help=False)
    timeline.add_argument("args", nargs=argparse.REMAINDER)

    open_cmd = sub.add_parser("open", help="用浏览器打开静态工作台（不启动服务）")
    open_cmd.add_argument("--workspace", help="workspaces/<name>")
    open_cmd.add_argument("--workbench", help="workbench.html 路径；默认 demo/workbench.html")
    open_cmd.add_argument("--no-open", dest="open", action="store_false", help="只打印路径，不打开浏览器")
    open_cmd.set_defaults(open=True)

    keys = sub.add_parser("keys", help="Key 管理（status/set/config/balance）", add_help=False)
    keys.add_argument("args", nargs=argparse.REMAINDER)

    quote = sub.add_parser("quote", help="按 config/models.json 估算费用")
    quote.add_argument("--model", default="muse-video-ext")
    quote.add_argument("--seconds", type=float, default=2)
    quote.add_argument("--images", type=int, default=1)
    quote.add_argument("--segments", type=int, default=1)

    check = sub.add_parser("check", help="检查 DATA 里的本地资产/视频是否存在")
    check.add_argument("--data", default="demo/data.json")
    check.add_argument("--workbench", help="workbench.html 路径；默认 DATA 同目录")

    init = sub.add_parser("init", help="从 demo 创建 workspaces/<name>")
    init.add_argument("name")

    build = sub.add_parser("build", help="用 DATA 构建 workbench.html")
    build.add_argument("--template", default="templates/workbench.html")
    build.add_argument("--data", default="demo/data.json")
    build.add_argument("--out", default="demo/workbench.html")
    return p


PASSTHROUGH = ("rh", "muse", "timeline", "keys")


def main():
    argv = list(sys.argv[1:])
    parser = build_parser()
    # 透传子命令必须在 argparse 之前整段截断。否则主解析器会把 `--prompt test`
    # 拆成 extras=["--prompt"] + REMAINDER=["test"]，下游收到缺值的 --prompt。
    if argv and argv[0] in PASSTHROUGH:
        args = argparse.Namespace(cmd=argv[0], args=argv[1:])
    else:
        args, extras = parser.parse_known_args()
        if extras:
            parser.error("unrecognized arguments: " + " ".join(extras))
    if not args.cmd:
        parser.print_help()
        return 0
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "demo":
        return cmd_demo(args)
    if args.cmd == "open":
        return cmd_open(args)
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
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "build":
        return cmd_build(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
