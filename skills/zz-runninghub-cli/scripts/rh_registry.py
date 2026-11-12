#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RunningHub 工作流注册表：查询、路由、渲染。

唯一真源：references/workflows.json
人读视图：references/workflows.md（由本脚本 render 生成，勿手改）

用法：
  python3 scripts/rh_registry.py list                 # 主线 + 备用
  python3 scripts/rh_registry.py list --all           # 全部（含候选/停用/帖子）
  python3 scripts/rh_registry.py list --status main --domain h3-video
  python3 scripts/rh_registry.py show 2110943749894402050
  python3 scripts/rh_registry.py show 终极篇
  python3 scripts/rh_registry.py find 换人
  python3 scripts/rh_registry.py route "我要给短剧出一段口播视频"
  python3 scripts/rh_registry.py render                # 重新生成 references/workflows.md
  python3 scripts/rh_registry.py validate              # 校验注册表
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "references" / "workflows.json"
OUT_PATH = ROOT / "references" / "workflows.md"

VALID_STATUS = {"main", "backup", "candidate", "untested", "deprecated"}
VALID_DOMAIN = {"h3-video", "image", "replace", "tts", "voice-convert", "upscale"}
VALID_KIND = {"workflow", "ai-app", "post", "unknown"}

STATUS_ORDER = {"main": 0, "backup": 1, "candidate": 2, "untested": 3, "deprecated": 4}
STATUS_LABEL = {
    "main": "主线",
    "backup": "备用",
    "candidate": "候选",
    "untested": "未测",
    "deprecated": "停用",
}


def load() -> dict:
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"找不到注册表：{DATA_PATH}")
    except json.JSONDecodeError as exc:
        sys.exit(f"注册表 JSON 解析失败：{exc}")


def entry_key(entry: dict) -> str:
    return entry.get("id") or f"post:{entry.get('post_id')}"


def domain_label(data: dict, entry: dict) -> str:
    return data.get("domains", {}).get(entry.get("domain"), entry.get("domain") or "-")


def sort_key(data: dict, entry: dict):
    domains = list(data.get("domains", {}).keys())
    domain_rank = domains.index(entry["domain"]) if entry.get("domain") in domains else 99
    return (
        STATUS_ORDER.get(entry.get("status"), 9),
        domain_rank,
        entry.get("priority", 99),
        entry.get("name", ""),
    )


def search_blob(entry: dict) -> str:
    parts = [
        entry.get("id") or "",
        entry.get("post_id") or "",
        entry.get("name") or "",
        entry.get("summary") or "",
        entry.get("domain") or "",
        entry.get("status") or "",
        entry.get("params") or "",
        entry.get("cost") or "",
        entry.get("endpoint") or "",
        entry.get("project") or "",
    ]
    for field in ("aliases", "used_by", "caveats", "docs"):
        parts.extend(entry.get(field) or [])
    return " ".join(str(p) for p in parts).lower()


def compact(data: dict, entry: dict) -> str:
    ident = entry_key(entry)
    domain = domain_label(data, entry)
    status = entry.get("status", "?")
    kind = entry.get("kind", "?")
    lines = [f"{ident}  [{status}/{domain}/{kind}] {entry.get('name', '')}"]
    meta = []
    if entry.get("cost"):
        meta.append(f"成本: {entry['cost']}")
    if entry.get("used_by"):
        meta.append("用在: " + ", ".join(entry["used_by"]))
    if meta:
        lines.append("    " + " ｜ ".join(meta))
    return "\n".join(lines)


def detail(data: dict, entry: dict) -> str:
    lines = [
        f"ID: {entry_key(entry)}",
        f"名称: {entry.get('name', '')}",
        f"状态: {entry.get('status')} / 域: {domain_label(data, entry)} / 形态: {entry.get('kind')}",
    ]
    if entry.get("project"):
        lines.append(f"项目: {entry['project']}")
    lines.append(f"用途: {entry.get('summary', '')}")
    if entry.get("endpoint"):
        lines.append(f"端点: {entry['endpoint']}")
    if entry.get("cost"):
        lines.append(f"成本: {entry['cost']}")
    if entry.get("params"):
        lines.append(f"参数: {entry['params']}")
    if entry.get("used_by"):
        lines.append("用在: " + ", ".join(entry["used_by"]))
    if entry.get("caveats"):
        lines.append("注意:")
        lines.extend(f"  - {c}" for c in entry["caveats"])
    if entry.get("docs"):
        lines.append("文档:")
        lines.extend(f"  - {d}" for d in entry["docs"])
    if entry.get("last_verified"):
        lines.append(f"最后验证: {entry['last_verified']}")
    return "\n".join(lines)


def resolve_workflow(data: dict, ident: str | None) -> dict | None:
    if not ident:
        return None
    for entry in data.get("workflows", []):
        if entry.get("id") == ident or entry.get("post_id") == ident:
            return entry
    return None


def cmd_list(data: dict, args) -> int:
    statuses = None
    if args.status:
        statuses = {s.strip() for s in args.status.split(",") if s.strip()}
    elif not args.all:
        statuses = {"main", "backup"}
    domains = None
    if args.domain:
        domains = {d.strip() for d in args.domain.split(",") if d.strip()}

    entries = []
    for entry in data.get("workflows", []):
        if statuses and entry.get("status") not in statuses:
            continue
        if domains and entry.get("domain") not in domains:
            continue
        entries.append(entry)
    entries.sort(key=lambda e: sort_key(data, e))

    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    if not entries:
        print("没有符合条件的登记项。")
        return 0
    for entry in entries:
        print(compact(data, entry))
    return 0


def cmd_show(data: dict, args) -> int:
    query = " ".join(args.query).strip()
    q = query.lower()
    entries = data.get("workflows", [])
    matches = [e for e in entries if q in {entry_key(e).lower(), (e.get("id") or "").lower(), (e.get("post_id") or "").lower()}]
    if not matches:
        matches = [
            e for e in entries
            if q in (e.get("name") or "").lower()
            or any(q in a.lower() for a in (e.get("aliases") or []))
        ]
    if not matches:
        matches = [e for e in entries if q in search_blob(e)]
    if not matches:
        print(f"没有找到：{query}")
        return 1
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return 0
    for i, entry in enumerate(matches):
        if i:
            print("\n" + "-" * 60)
        print(detail(data, entry))
    return 0


def cmd_find(data: dict, args) -> int:
    query = " ".join(args.query).strip().lower()
    entries = [e for e in data.get("workflows", []) if query in search_blob(e)]
    entries.sort(key=lambda e: sort_key(data, e))
    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    if not entries:
        print(f"没有找到：{query}")
        return 1
    for entry in entries:
        print(compact(data, entry))
    return 0


def workflow_keyword_score(query: str, entry: dict) -> int:
    q = query.lower()
    score = 0
    for alias in entry.get("aliases") or []:
        if alias.lower() in q:
            score += 6
    if (entry.get("name") or "").lower() in q:
        score += 4
    if q in (entry.get("summary") or "").lower():
        score += 2
    for used in entry.get("used_by") or []:
        if used.lower() in q:
            score += 1
    return score


def workflow_score(query: str, entry: dict, domains: set[str]) -> int:
    score = workflow_keyword_score(query, entry)
    if score == 0:
        return 0
    status = entry.get("status")
    score += {"main": 3, "backup": 1, "candidate": 0, "untested": 0, "deprecated": -8}.get(status, 0)
    if entry.get("domain") in domains:
        score += 3
    return score


def classify_domains(query: str) -> set[str]:
    q = query.lower()
    hints = {
        "h3-video": ["视频", "出片", "分镜", "口播", "成片", "漫剧", "课文", "短片", "首帧", "图生"],
        "image": ["图", "资产", "定妆", "场景", "道具", "文生图", "海报"],
        "replace": ["换人", "替换", "人物"],
        "tts": ["配音", "声音", "克隆", "tts", "旁白"],
        "voice-convert": ["音色", "vc", "迁移"],
        "upscale": ["超分", "清晰", "1080", "放大"],
    }
    return {domain for domain, words in hints.items() if any(w in q for w in words)}


def cmd_route(data: dict, args) -> int:
    query = " ".join(args.query).strip()
    q = query.lower()
    domains = classify_domains(query)

    route_hits = []
    for route in data.get("routes", []):
        matched = [m for m in route.get("match", []) if m.lower() in q]
        score = (max((len(m) for m in matched), default=0) * 10) + len(matched) * 2
        if route.get("task", "").lower() in q:
            score += 5
        if score:
            route_hits.append((score, matched, route))
    route_hits.sort(key=lambda x: -x[0])

    print(f"任务：{query}")
    if route_hits:
        print("\n推荐路径：")
        for score, matched, route in route_hits[:3]:
            print(f"- {route['task']}  （命中：{'/'.join(matched)}）")
            wf = resolve_workflow(data, route.get("workflow"))
            if wf:
                print(f"  工作流：{entry_key(wf)}  {wf['name']}  [{wf['status']}/{domain_label(data, wf)}]")
                if wf.get("cost"):
                    print(f"  成本：{wf['cost']}")
                print(f"  下一步：{route.get('note', '')}")
            else:
                print(f"  不是单条工作流：{route.get('note', '')}")
    elif route_hits:
        print("\n预设路由命中，不再展开候选；要看同域其他项：`list --domain <域>`。")
    else:
        print("\n没有命中预设路由，按工作流关键词匹配：")

    if route_hits and route_hits[0][0] >= 10:
        return 0

    scored = []
    for entry in data.get("workflows", []):
        score = workflow_score(query, entry, domains)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: (-x[0], sort_key(data, x[1])))

    if scored:
        print("\n候选工作流：")
        for score, entry in scored[:5]:
            print(f"- {entry_key(entry)}  {entry['name']}  ({score} 分, {entry['status']}/{domain_label(data, entry)})")
            if entry.get("summary"):
                print(f"  {entry['summary']}")
    elif not route_hits:
        print("没有匹配。先跑 `list --all` 或 `find <关键词>`。")
    return 0


def md_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = "；".join(str(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def cmd_render(data: dict, args) -> int:
    out = Path(args.out) if args.out else OUT_PATH
    domains = data.get("domains", {})
    updated = data.get("updated", "")
    defaults = data.get("defaults", {})

    lines = [
        "# RunningHub 工作流总表",
        "",
        f"> 机器可读真源：`references/workflows.json`（Updated {updated}）",
        "> 本文件由 `python3 scripts/rh_registry.py render` 生成，**勿手改**。",
        f"> 默认：{defaults.get('key', 'consumer')} key，{defaults.get('concurrency', 3)} 并发。{defaults.get('note', '')}",
        "",
        "## 怎么用",
        "",
        "```bash",
        "python3 scripts/rh_registry.py route \"我要做的事\"   # 不知道选哪个：先问它",
        "python3 scripts/rh_registry.py show <ID|别名>       # 看参数/成本/坑",
        "python3 scripts/rh_registry.py find <关键词>        # 搜全表",
        "python3 scripts/rh_registry.py list --all           # 全部登记项",
        "```",
        "",
        "## 30 秒路由",
        "",
        "| 我要… | 工作流 | 说明 |",
        "|---|---|---|",
    ]
    for route in data.get("routes", []):
        wf = resolve_workflow(data, route.get("workflow"))
        if wf:
            ident = f"`{entry_key(wf)}` {wf['name']}"
        else:
            ident = "—"
        lines.append(f"| {md_cell(route.get('task'))} | {md_cell(ident)} | {md_cell(route.get('note'))} |")

    sections = [
        ("主线", {"main"}),
        ("备用", {"backup"}),
        ("候选 / 未测", {"candidate", "untested"}),
        ("停用", {"deprecated"}),
    ]
    for title, statuses in sections:
        entries = [e for e in data.get("workflows", []) if e.get("status") in statuses and e.get("kind") != "post"]
        entries.sort(key=lambda e: sort_key(data, e))
        lines.extend(["", f"## {title}", ""])
        if not entries:
            lines.append("（无）")
            continue
        lines.append("| ID | 名称 | 域/形态 | 成本 | 用在 | 注意 |")
        lines.append("|---|---|---|---|---|---|")
        for entry in entries:
            lines.append(
                "| `{id}` | {name} | {domain}/{kind} | {cost} | {used} | {caveat} |".format(
                    id=md_cell(entry_key(entry)),
                    name=md_cell(entry.get("name")),
                    domain=md_cell(domains.get(entry.get("domain"), entry.get("domain"))),
                    kind=md_cell(entry.get("kind")),
                    cost=md_cell(entry.get("cost")),
                    used=md_cell(entry.get("used_by")),
                    caveat=md_cell((entry.get("caveats") or [])[:2]),
                )
            )

    posts = [e for e in data.get("workflows", []) if e.get("kind") == "post"]
    posts.sort(key=lambda e: e.get("priority", 99))
    lines.extend(["", "## 只收藏未接入（帖子，不是 workflowId）", ""])
    if posts:
        lines.append("| 帖子 | 名称 | 域 | 说明 |")
        lines.append("|---|---|---|---|")
        for entry in posts:
            lines.append(
                f"| `post/{md_cell(entry.get('post_id'))}` | {md_cell(entry.get('name'))} | "
                f"{md_cell(domains.get(entry.get('domain'), entry.get('domain')))} | {md_cell(entry.get('summary'))} |"
            )
        lines.extend([
            "",
            "> 这些只有 RH 帖子 ID，必须先在自己的账号里打开并保存一次，才能拿到可 API 调用的 workflowId。",
        ])
    else:
        lines.append("（无）")

    lines.extend([
        "",
        "## 维护规则",
        "",
        "1. 新增/改状态只改 `references/workflows.json`，再跑 `python3 scripts/rh_registry.py render`。",
        "2. 项目文档可以写“本项目固定用哪个 ID”，但不要另建一份总表；总表以本文件为准。",
        "3. 状态变化：跑通一次才从 `candidate` 升 `main`/`backup`；实测有问题降 `deprecated` 并写清原因。",
        "4. 帖子候选只有换成 workflowId 后，才登记 `id` 并补 `endpoint`/`params`。",
        "",
    ])

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成：{out}")
    return 0


def cmd_validate(data: dict, args) -> int:
    errors = []
    workflows = data.get("workflows")
    if data.get("schema_version") != 1:
        errors.append("schema_version 必须是 1")
    if not isinstance(workflows, list) or not workflows:
        errors.append("workflows 必须是非空数组")
        workflows = []

    seen = {}
    for i, entry in enumerate(workflows):
        where = f"workflows[{i}]"
        for field in ("kind", "name", "domain", "status", "summary"):
            if not entry.get(field):
                errors.append(f"{where}: 缺少 {field}")
        if entry.get("kind") not in VALID_KIND:
            errors.append(f"{where}: kind={entry.get('kind')} 非法")
        if entry.get("domain") not in VALID_DOMAIN:
            errors.append(f"{where}: domain={entry.get('domain')} 非法")
        if entry.get("status") not in VALID_STATUS:
            errors.append(f"{where}: status={entry.get('status')} 非法")
        ident = entry_key(entry)
        if ident in seen:
            errors.append(f"{where}: 重复标识 {ident}（另见 {seen[ident]}）")
        seen[ident] = where
        if entry.get("id") and (not str(entry["id"]).isdigit() or len(str(entry["id"])) != 19):
            errors.append(f"{where}: id 不是 19 位数字：{entry['id']}")
        if entry.get("post_id") and (not str(entry["post_id"]).isdigit() or len(str(entry["post_id"])) != 19):
            errors.append(f"{where}: post_id 不是 19 位数字：{entry['post_id']}")
        if not entry.get("id") and not entry.get("post_id"):
            errors.append(f"{where}: id 与 post_id 至少有一个")
        if entry.get("kind") == "post" and entry.get("id"):
            errors.append(f"{where}: kind=post 不应同时有 id")
        if entry.get("kind") != "post" and not entry.get("id"):
            errors.append(f"{where}: kind={entry.get('kind')} 必须有 id")

    for i, route in enumerate(data.get("routes", [])):
        if not route.get("task"):
            errors.append(f"routes[{i}]: 缺少 task")
        if not route.get("match"):
            errors.append(f"routes[{i}]: 缺少 match")
        wf_id = route.get("workflow")
        if wf_id and not resolve_workflow(data, wf_id):
            errors.append(f"routes[{i}]: workflow {wf_id} 不在 workflows 中")

    if errors:
        print("校验失败：")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"OK：{len(workflows)} 条登记，{len(data.get('routes', []))} 条路由")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="RunningHub 工作流注册表")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="列出登记项（默认主线+备用）")
    p.add_argument("--all", action="store_true", help="包含候选/未测/停用/帖子")
    p.add_argument("--status", help="逗号分隔，如 main,backup")
    p.add_argument("--domain", help="逗号分隔，如 h3-video,image")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="按 ID/帖子/别名/名称查详情")
    p.add_argument("query", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("find", help="全文搜索")
    p.add_argument("query", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("route", help="按任务描述推荐工作流")
    p.add_argument("query", nargs="+")
    p.set_defaults(func=cmd_route)

    p = sub.add_parser("render", help="从 JSON 生成 references/workflows.md")
    p.add_argument("--out", help="输出路径（默认 references/workflows.md）")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("validate", help="校验注册表")
    p.set_defaults(func=cmd_validate)

    args = ap.parse_args()
    data = load()
    return args.func(data, args)


if __name__ == "__main__":
    sys.exit(main())
