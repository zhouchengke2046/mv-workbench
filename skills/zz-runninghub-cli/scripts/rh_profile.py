#!/usr/bin/env python3
"""
zz-rhcli 自进化记忆脚本：记录用户使用习惯 + 工作流目录（curated registry）。

数据存于 ~/.runninghub/profile.json（所有 Agent 共享同一份记忆）。
能力目录默认读取上游官方共享仓（~/TraeWork/runninghub-upstream），
可通过 --caps 或环境变量 RUNNINGHUB_CAPABILITIES 覆盖。
纯 Python 标准库，零依赖。

命令:
  get                                       打印完整 profile
  set <key> <value>                         记录偏好（如 video_model / duration / aspect_ratio / lang）
  alias <alias> <endpoint>                  注册用户别名（如 "可灵" -> kling-v3.0-pro/text-to-video）
  record <endpoint> [--task TASK] [--status success|failed] [--cost F] [--duration S] [--quality 1-5]
                                           记录一次调用（成功/失败/成本/时长/质量 → 影响 suggest 排序与降级）
  suggest <task> [--top N] [--caps PATH]    按 熟悉度+成功率+质量+成本+流行度 推荐端点（自进化路由）
  workflow add <webappId> --task T [--title S] [--note S] [--inputs a,b] [--cost low|med|high]
                                           工作流入库（发现可用工作流后沉淀）
  workflow search <keyword>                 在自建目录搜工作流（平台无关键词搜索 API）
  workflow list [--task T]                  按分类列出目录
  workflow verify <webappId>                标记已验证（跑成功一次后调用）
  workflow rm <webappId>                    从目录移除

工作流发现飞轮：
  用户要"找个能做 X 的工作流"且无链接 -> 1) workflow search X
  -> 2) 未命中则 runninghub_app.py --list --sort HOTTEST/NEWEST 浏览
  -> 3) --info 确认节点输入匹配 -> 4) 跑成功 -> workflow verify + workflow add 入库

自进化闭环（每次任务都走）：
  前置 get 读偏好 -> 执行生成 -> record（status/cost/quality 全量记录）
  -> 用户表达稳定偏好 set/alias -> 不确定时 suggest（成功率+质量+成本+熟悉度加权）
  失败经验：record --status failed 会沉淀，suggest 自动降级高失败率端点
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

SCRIPT_DIR = Path(__file__).resolve().parent

# profile 放共享位置：所有 Agent 读写同一份习惯记忆
PROFILE_PATH = Path.home() / ".runninghub" / "profile.json"
# 锁文件（与 profile 同目录，独立文件避免读写冲突）
LOCK_PATH = Path.home() / ".runninghub" / "profile.lock"

# 上游官方 skill 目录（共享仓，git pull 保持最新）
# 解析顺序：环境变量 RH_UPSTREAM_DIR > 候选路径中第一个存在的 > 历史默认值（便于报错定位）
# 历史：上游目录原在 ~/TraeWork/，后迁至 ~/github/；用候选列表兼容两种布局，避免路径漂移导致找不到 capabilities.json
_UPSTREAM_CANDIDATES = [
    Path.home() / "TraeWork" / "runninghub-upstream" / "runninghub",
    Path.home() / "github" / "runninghub-upstream" / "runninghub",
]
_env_upstream = os.environ.get("RH_UPSTREAM_DIR")
if _env_upstream:
    UPSTREAM_DIR = Path(_env_upstream)
else:
    UPSTREAM_DIR = next(
        (p for p in _UPSTREAM_CANDIDATES if p.is_dir()),
        _UPSTREAM_CANDIDATES[0],
    )
DEFAULT_CAPABILITIES = UPSTREAM_DIR / "data" / "capabilities.json"

DEFAULT_PROFILE = {
    "preferences": {},  # {"duration": "10", "aspect_ratio": "16:9", "lang": "en", ...}
    "usage": {},        # {endpoint: {count, success_count, fail_count, tasks, total_cost, last_cost, avg_quality, recent}}
    "aliases": {},      # {"可灵": "kling-v3.0-pro/text-to-video", ...}
    "workflows": {},    # {task_category: [{"webappId","title","note","inputs","cost","verified"}]}
}

MAX_RECENT = 10  # 每个端点保留最近 10 条调用记录


def _acquire_lock():
    """获取文件锁（多 Agent 并发安全）。非阻塞，拿不到锁则等待。"""
    if not _HAS_FCNTL:
        return None
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(LOCK_PATH, "w")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # 阻塞式排他锁
    return lock_file


def _release_lock(lock_file) -> None:
    """释放文件锁。"""
    if lock_file is None:
        return
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
    except Exception:
        pass


def load() -> dict:
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        for k, v in DEFAULT_PROFILE.items():
            data.setdefault(k, dict(v))
        return data
    return json.loads(json.dumps(DEFAULT_PROFILE))


def save(data: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_get() -> None:
    print(json.dumps(load(), ensure_ascii=False, indent=2))


def cmd_set(key: str, value: str) -> None:
    lock = _acquire_lock()
    try:
        data = load()
        data["preferences"][key] = value
        save(data)
        print(f"preferences.{key} = {value}")
    finally:
        _release_lock(lock)


def cmd_alias(alias: str, endpoint: str) -> None:
    lock = _acquire_lock()
    try:
        data = load()
        data["aliases"][alias] = endpoint
        save(data)
        print(f"alias: {alias} -> {endpoint}")
    finally:
        _release_lock(lock)


def cmd_record(endpoint: str, task: str | None, status: str,
               cost: float | None, duration: int | None, quality: int | None) -> None:
    """记录一次调用，含状态/成本/时长/质量。失败也记 —— 失败经验影响 suggest 排序。"""
    lock = _acquire_lock()
    try:
        data = load()
        usage = data["usage"].setdefault(endpoint, {})
        # 兼容旧数据结构（无 success_count 等字段时补全）
        for k, default in [
            ("count", 0), ("success_count", 0), ("fail_count", 0),
            ("tasks", []), ("total_cost", 0.0), ("recent", [],), ("avg_quality", 0.0),
        ]:
            usage.setdefault(k, default if isinstance(default, (int, float)) else list(default) if isinstance(default, list) else default)

        usage["count"] += 1
        if status == "success":
            usage["success_count"] += 1
        elif status == "failed":
            usage["fail_count"] += 1

        if task and task not in usage["tasks"]:
            usage["tasks"].append(task)

        # 成本累计
        if cost is not None:
            usage["total_cost"] = round(usage["total_cost"] + cost, 4)
            usage["last_cost"] = cost

        # 质量滚动平均（仅成功时记录质量，避免失败拖低分数）
        if quality is not None and status == "success":
            sc = usage["success_count"]
            old_avg = usage.get("avg_quality", 0.0)
            if sc > 0:
                usage["avg_quality"] = round((old_avg * (sc - 1) + quality) / sc, 2)

        # 最近历史（最多 MAX_RECENT 条）
        entry: dict = {"status": status}
        if cost is not None:
            entry["cost"] = cost
        if duration is not None:
            entry["duration"] = duration
        if quality is not None:
            entry["quality"] = quality
        usage["recent"].append(entry)
        if len(usage["recent"]) > MAX_RECENT:
            usage["recent"] = usage["recent"][-MAX_RECENT:]

        save(data)
    finally:
        _release_lock(lock)
    sc = usage["success_count"]
    fc = usage["fail_count"]
    rate = round(sc / usage["count"] * 100, 1) if usage["count"] else 0
    print(f"recorded {endpoint} (total={usage['count']} success={sc} fail={fc} rate={rate}%)")


def cmd_suggest(task: str, top: int, caps_arg: str | None) -> None:
    """推荐端点。用过的按综合分（成功率+质量+成本+熟悉度）排，没用过的按流行度排。"""
    caps_path = (
        Path(caps_arg)
        if caps_arg
        else Path(os.environ.get("RUNNINGHUB_CAPABILITIES", str(DEFAULT_CAPABILITIES)))
    )
    if not caps_path.exists():
        print(
            f"Error: capabilities.json not found at {caps_path}. "
            "请确认上游已 clone（见 SKILL.md『上游』一节），或传 --caps 指定路径。",
            file=sys.stderr,
        )
        sys.exit(1)
    caps = json.loads(caps_path.read_text(encoding="utf-8"))
    profile = load()

    # 统一排序：用过的按综合分，没用过的给基准分 0.5 + 流行度微调
    # 这样 100% 失败的端点（score≈0）会自然沉到 new 端点后面
    all_list: list[tuple] = []  # (final_score, count, ep, usage)

    for ep in caps["endpoints"]:
        if ep["task"] != task:
            continue
        u = profile["usage"].get(ep["endpoint"], {})
        count = u.get("count", 0)

        if count > 0:
            success = u.get("success_count", 0)
            fail = u.get("fail_count", 0)
            avg_q = u.get("avg_quality", 0.0)
            last_cost = u.get("last_cost", 0.0)

            # 综合分：成功率 40% + 质量 30% + 成本反向 20% + 熟悉度 10%
            rate = success / count
            quality_norm = (avg_q / 5.0) if avg_q else 0.5
            cost_norm = (1.0 / (1.0 + last_cost)) if last_cost > 0 else 0.5
            familiarity = min(count / 10.0, 1.0)
            score = rate * 0.4 + quality_norm * 0.3 + cost_norm * 0.2 + familiarity * 0.1

            # 失败率惩罚（至少 3 次才启用，避免小样本误判）
            if count >= 3 and fail > 0:
                fail_rate = fail / count
                if fail_rate >= 0.5:
                    score *= 0.5
                elif fail_rate >= 0.3:
                    score *= 0.8

            all_list.append((score, count, ep, u))
        else:
            pop = ep["popularity"] if ep["popularity"] < 99 else 999
            # new 端点基准 0.5，流行度微调（0.5 ~ 0.6）
            base = 0.5 + min(pop, 20) / 200
            all_list.append((base, 0, ep, {}))

    all_list.sort(key=lambda x: -x[0])
    picked = all_list[:top]
    if not picked:
        print(f"No endpoint found for task '{task}'", file=sys.stderr)
        sys.exit(1)

    print(f"Suggest {len(picked)} endpoint(s) for task '{task}':")
    for score, used_count, ep, u in picked:
        if used_count > 0:
            sc = u.get("success_count", 0)
            rate = round(sc / used_count * 100) if used_count else 0
            q = u.get("avg_quality", 0.0)
            c = u.get("last_cost", 0.0)
            mark = f"[USED x{used_count} rate={rate}% q={q} ¥{c}]"
        else:
            mark = "          "
        print(f"  {mark} {ep['endpoint']:55s} {ep['name_cn']}")


# ---------------------------------------------------------------------------
# workflow 目录（curated registry）
# ---------------------------------------------------------------------------

def cmd_wf_add(webapp_id: str, task: str, title: str, note: str,
               inputs: str, cost: str) -> None:
    lock = _acquire_lock()
    try:
        data = load()
        cat = data["workflows"].setdefault(task, [])
        for e in cat:
            if e["webappId"] == webapp_id:
                print(f"already exists in [{task}]: {webapp_id}")
                return
        entry = {
            "webappId": webapp_id,
            "title": title,
            "note": note,
            "inputs": [i.strip() for i in inputs.split(",")] if inputs else [],
            "cost": cost,
            "verified": False,
        }
        cat.append(entry)
        save(data)
        print(f"workflow added -> [{task}] {webapp_id} {title or ''}")
    finally:
        _release_lock(lock)


def cmd_wf_search(keyword: str) -> None:
    data = load()
    k = keyword.lower()
    hits = []
    for task, entries in data["workflows"].items():
        for e in entries:
            hay = " ".join([e.get("title", ""), e.get("note", ""), task]).lower()
            if k in hay:
                hits.append((task, e))
    if not hits:
        print(
            f"No curated workflow matches '{keyword}'. "
            "平台无关键词搜索 API，可 runninghub_app.py --list --sort HOTTEST/NEWEST 浏览；"
            "发现可用后 workflow add 入库。"
        )
        return
    for task, e in hits:
        mark = "✓" if e.get("verified") else "?"
        print(f"[{mark}] [{task}] {e['webappId']}  {e.get('title', '')}")
        if e.get("note"):
            print(f"      note: {e['note']}")
        if e.get("inputs"):
            print(f"      inputs: {', '.join(e['inputs'])}")


def cmd_wf_list(task: str | None) -> None:
    data = load()
    wf = data["workflows"]
    if not wf:
        print("工作流目录为空。发现可用工作流后请 `workflow add` 入库（跨 Agent 共享）。")
        return
    for t, entries in sorted(wf.items()):
        if task and t != task:
            continue
        print(f"[{t}] ({len(entries)} 个)")
        for e in entries:
            mark = "✓" if e.get("verified") else "?"
            print(f"  {mark} {e['webappId']}  {e.get('title', '')}")
            if e.get("note"):
                print(f"      {e['note']}")


def cmd_wf_verify(webapp_id: str) -> None:
    lock = _acquire_lock()
    try:
        data = load()
        for entries in data["workflows"].values():
            for e in entries:
                if e["webappId"] == webapp_id:
                    e["verified"] = True
                    save(data)
                    print(f"verified {webapp_id}")
                    return
        print(f"not found in catalog: {webapp_id}（先 workflow add）", file=sys.stderr)
    finally:
        _release_lock(lock)


def cmd_wf_rm(webapp_id: str) -> None:
    lock = _acquire_lock()
    try:
        data = load()
        removed = 0
        for t, entries in list(data["workflows"].items()):
            new_list = [e for e in entries if e["webappId"] != webapp_id]
            if len(new_list) != len(entries):
                removed += len(entries) - len(new_list)
            data["workflows"][t] = new_list
        if removed:
            save(data)
        print(f"removed {removed} entry(ies) for {webapp_id}")
    finally:
        _release_lock(lock)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="zz-rhcli self-evolving usage profile + workflow catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="print full profile")
    p_get.set_defaults(fn=cmd_get)

    p_set = sub.add_parser("set", help="set a preference")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.set_defaults(fn=cmd_set)

    p_alias = sub.add_parser("alias", help="register a user alias -> endpoint")
    p_alias.add_argument("alias")
    p_alias.add_argument("endpoint")
    p_alias.set_defaults(fn=cmd_alias)

    p_record = sub.add_parser("record", help="record a call (success/failed + cost/quality)")
    p_record.add_argument("endpoint")
    p_record.add_argument("--task", default=None)
    p_record.add_argument("--status", choices=["success", "failed"], default="success",
                          help="调用结果（默认 success；failed 也会沉淀影响排序）")
    p_record.add_argument("--cost", type=float, default=None, help="本次花费 ¥")
    p_record.add_argument("--duration", type=int, default=None, help="生成耗时(秒)")
    p_record.add_argument("--quality", type=int, default=None, choices=[1, 2, 3, 4, 5],
                          help="质量评分 1-5（仅成功时纳入平均）")
    p_record.set_defaults(fn=cmd_record)

    p_suggest = sub.add_parser("suggest", help="suggest endpoints for a task")
    p_suggest.add_argument("task")
    p_suggest.add_argument("--top", type=int, default=3)
    p_suggest.add_argument("--caps", default=None, help="override capabilities.json path")
    p_suggest.set_defaults(fn=cmd_suggest)

    # workflow 目录
    p_wf = sub.add_parser("workflow", help="curated workflow catalog")
    wf_sub = p_wf.add_subparsers(dest="wf_cmd", required=True)

    p_wadd = wf_sub.add_parser("add", help="add a workflow to catalog")
    p_wadd.add_argument("webapp_id")
    p_wadd.add_argument("--task", required=True)
    p_wadd.add_argument("--title", default="")
    p_wadd.add_argument("--note", default="")
    p_wadd.add_argument("--inputs", default="")
    p_wadd.add_argument("--cost", choices=["low", "med", "high"], default="med")
    p_wadd.set_defaults(wf_fn=cmd_wf_add)

    p_wsearch = wf_sub.add_parser("search", help="search curated catalog")
    p_wsearch.add_argument("keyword")
    p_wsearch.set_defaults(wf_fn=cmd_wf_search)

    p_wlist = wf_sub.add_parser("list", help="list catalog by task")
    p_wlist.add_argument("--task", default=None)
    p_wlist.set_defaults(wf_fn=cmd_wf_list)

    p_wverify = wf_sub.add_parser("verify", help="mark a workflow as verified")
    p_wverify.add_argument("webapp_id")
    p_wverify.set_defaults(wf_fn=cmd_wf_verify)

    p_wrm = wf_sub.add_parser("rm", help="remove a workflow from catalog")
    p_wrm.add_argument("webapp_id")
    p_wrm.set_defaults(wf_fn=cmd_wf_rm)

    args = parser.parse_args()
    if args.cmd == "get":
        args.fn()
    elif args.cmd == "set":
        args.fn(args.key, args.value)
    elif args.cmd == "alias":
        args.fn(args.alias, args.endpoint)
    elif args.cmd == "record":
        args.fn(args.endpoint, args.task, args.status, args.cost, args.duration, args.quality)
    elif args.cmd == "suggest":
        args.fn(args.task, args.top, args.caps)
    elif args.cmd == "workflow":
        fn = args.wf_fn
        if args.wf_cmd == "add":
            fn(args.webapp_id, args.task, args.title, args.note, args.inputs, args.cost)
        elif args.wf_cmd == "search":
            fn(args.keyword)
        elif args.wf_cmd == "list":
            fn(args.task)
        elif args.wf_cmd == "verify":
            fn(args.webapp_id)
        elif args.wf_cmd == "rm":
            fn(args.webapp_id)


if __name__ == "__main__":
    main()
