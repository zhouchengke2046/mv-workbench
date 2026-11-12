#!/usr/bin/env python3
"""扫描 RunningHub 工作流榜单，按关键词本地过滤（RH 服务端不支持搜索）。

用法：
    RUNNINGHUB_API_KEY=xxx python scan_apps.py 换人 人物替换 角色替换
    python scan_apps.py --pages 24 --sort HOTTEST:7 --sort RECOMMEND 关键词...

输出：命中清单（按榜单原始顺序 = 官方热度排名），并写出 rh_pool.json / rh_hits.json。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

LIST_URL = "https://www.runninghub.cn/openapi/v2/aiapp/list"


def call_list(api_key: str, payload: dict) -> dict:
    req = urllib.request.Request(
        LIST_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def job(api_key: str, spec: tuple[str, int | None, int]) -> tuple:
    sort, days, page = spec
    payload = {"current": page, "size": 50, "sort": sort}
    if days:
        payload["days"] = days
    try:
        records = call_list(api_key, payload).get("data", {}).get("records", [])
    except Exception as exc:  # noqa: BLE001
        records = []
        print(f"  ! {sort} p{page} 失败: {exc}", file=sys.stderr)
    return sort, days, page, records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="+", help="本地过滤关键词")
    ap.add_argument("--pages", type=int, default=24, help="每个榜单抓取页数（每页 50 条）")
    ap.add_argument("--sort", dest="sorts", action="append", default=None,
                    help="榜单，格式 SORT 或 SORT:DAYS，如 HOTTEST:7 / RECOMMEND。可重复")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    api_key = os.environ.get("RUNNINGHUB_API_KEY")
    if not api_key:
        print("缺少环境变量 RUNNINGHUB_API_KEY", file=sys.stderr)
        return 2

    sort_specs: list[tuple[str, int | None]] = []
    for raw in (args.sorts or ["HOTTEST:7", "HOTTEST:30", "HOTTEST:90", "RECOMMEND", "NEWEST"]):
        if ":" in raw:
            s, d = raw.split(":", 1)
            sort_specs.append((s.upper(), int(d)))
        else:
            sort_specs.append((raw.upper(), None))

    jobs = [(s, d, p) for s, d in sort_specs for p in range(1, args.pages + 1)]
    with ThreadPoolExecutor(args.workers) as ex:
        results = list(ex.map(lambda spec: job(api_key, spec), jobs))

    pool: dict[str, dict] = {}
    for sort, days, page, records in results:
        tag = f"{sort}{days}日" if days else sort
        for i, rec in enumerate(records):
            m = re.search(r"run/ai-app/(\d+)", rec.get("invokeExample") or "")
            if not m:
                continue
            wid = m.group(1)
            if wid in pool:
                continue
            pool[wid] = {
                "webappId": wid,
                "title": (rec.get("title") or "").strip(),
                "desc": (rec.get("description") or "").strip(),
                "sortTag": tag,
                "sortKey": page * 1000 + i,
                "cover": rec.get("cover") or "",
                "invoke": rec.get("invokeExample") or "",
            }

    hits = []
    for item in pool.values():
        text = item["title"] + " " + item["desc"]
        matched = [k for k in args.keywords if k in text]
        if matched:
            hits.append({**item, "matched": matched})

    order = [f"{s}{d}日" if d else s for s, d in sort_specs]
    print(f"榜单: {order} | 请求 {len(jobs)} 次 | 去重工作流 {len(pool)} 条 | 命中 {len(hits)} 条")
    for tag in order:
        group = sorted([h for h in hits if h["sortTag"] == tag], key=lambda x: x["sortKey"])
        if not group:
            continue
        print(f"\n===== {tag} 命中 {len(group)} 条（顺序即官方榜内排名）=====")
        for h in group:
            print(f"  p{h['sortKey'] // 1000:<2d}#{h['sortKey'] % 1000 + 1:<3d} {h['webappId']}  "
                  f"{h['title'][:52]}  <{','.join(h['matched'])}>")

    json.dump(pool, open(os.path.join(args.out, "rh_pool.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(hits, open(os.path.join(args.out, "rh_hits.json"), "w"), ensure_ascii=False, indent=1)
    print(f"\n已写出 rh_pool.json / rh_hits.json -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
