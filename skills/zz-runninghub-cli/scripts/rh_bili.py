#!/usr/bin/env python3
"""
rh_bili.py — B站视频 → RunningHub 工作流发现

输入 B 站视频 URL / BV 号，自动抓取视频信息 + 简介 + 评论区（前若干条），
扫描其中所有 RunningHub 工作流链接，供 agent 分析视频介绍的功能并测试工作流。

纯 Python 标准库（urllib + json + re），零第三方依赖。

用法:
  python3 rh_bili.py <url|bvid> [--comments N] [--pages N]
  --comments N  扫描评论条数上限（默认 98）
  --pages N     评论翻页数（默认 2，每页 20 条）

Cookie（可选，用于全量评论）：
  环境变量 BILI_COOKIE 或文件 ~/.bilibili/cookie.txt（内容为 SESSDATA=xxx 等）

示例:
  python3 rh_bili.py https://www.bilibili.com/video/BV1xxxx
  python3 rh_bili.py BV1xxxx --pages 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
REFERER = "https://www.bilibili.com"
COOKIE_FILE = Path.home() / ".bilibili" / "cookie.txt"

BV_RE = re.compile(r"BV[0-9A-Za-z]{10}")
# 兼容 带协议 / 裸域名（B站评论里 UP 主常直接贴 runninghub.cn/... 无协议头）
RH_LINK_RE = re.compile(
    r"(?:https?://)?(?:www\.)?runninghub\.(?:cn|ai)(?:/[^\s\"'<>，。；、)】\]}]*)?",
    re.IGNORECASE,
)
RH_APP_ID_RE = re.compile(r"/ai-detail/(\d+)")


def resolve_cookie() -> str | None:
    """Cookie 优先级：环境变量 BILI_COOKIE > ~/.bilibili/cookie.txt。"""
    env = os.environ.get("BILI_COOKIE", "").strip()
    if env:
        return env
    if COOKIE_FILE.exists():
        text = COOKIE_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def http_get(url: str, cookie: str | None = None) -> dict:
    headers = {"User-Agent": UA, "Referer": REFERER}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_bvid(text: str) -> str:
    m = BV_RE.search(text)
    if not m:
        print(json.dumps({"error": "NO_BVID", "message": "无法从输入中解析 BV 号"}, ensure_ascii=False))
        sys.exit(1)
    return m.group(0)


def fetch_video(bvid: str, cookie: str | None = None) -> dict:
    data = http_get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", cookie)
    if data.get("code") != 0:
        print(json.dumps({"error": "VIDEO_FETCH_FAILED", "message": data.get("message", "")},
                         ensure_ascii=False))
        sys.exit(1)
    d = data["data"]
    return {
        "bvid": bvid,
        "aid": d.get("aid"),
        "title": d.get("title", ""),
        "owner": d.get("owner", {}).get("name", ""),
        "desc": (d.get("desc") or "").strip(),
        "pic": d.get("pic", ""),
    }


def fetch_comments(aid: int, pages: int, cookie: str | None = None) -> list[str]:
    texts = []
    for page in range(1, pages + 1):
        try:
            data = http_get(
                f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&sort=1&pn={page}&ps=20",
                cookie,
            )
        except Exception:
            break
        d = data.get("data") or {}
        replies = d.get("replies") or []
        if not replies:
            break
        for r in replies:
            msg = (r.get("content") or {}).get("message", "")
            if msg:
                texts.append(f"{r.get('member', {}).get('uname', '?')}: {msg}")
    return texts


def collect_links(desc: str, comments: list[str], all_links: bool) -> dict:
    found: dict[str, dict] = {}  # key=link, value={source, context}

    def scan(text: str, source: str, context: str) -> None:
        for m in RH_LINK_RE.finditer(text):
            link = m.group(0).rstrip(".,，。;；!！")
            # 只保留工作流相关路径（ai-detail / 数字结尾），并输出全链接便于核对
            if not all_links:
                if "/ai-detail/" not in link and not re.search(r"/\d+\s*$", link):
                    continue
            if link not in found:
                found[link] = {"source": source, "context": context}

    scan(desc, "desc", "视频简介")
    for i, c in enumerate(comments[:98]):
        scan(c, "comment", f"评论区 #{i + 1}")

    # 从链接中提取 webappId
    results = []
    for link, meta in found.items():
        m = RH_APP_ID_RE.search(link)
        webapp_id = m.group(1) if m else None
        results.append({"url": link, "webappId": webapp_id, "source": meta["source"]})

    return {"links": results, "raw_links": list(found.keys())}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="B站视频 → RunningHub 工作流发现",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="B站视频 URL 或 BV 号")
    parser.add_argument("--comments", type=int, default=98, help="扫描评论条数上限（默认 98）")
    parser.add_argument("--pages", type=int, default=2, help="评论翻页数（默认 2，每页 20）")
    parser.add_argument("--all", action="store_true", help="输出全部 runninghub 链接（默认只保留工作流相关）")
    args = parser.parse_args()

    bvid = extract_bvid(args.input)
    cookie = resolve_cookie()
    video = fetch_video(bvid, cookie)
    comments = fetch_comments(video["aid"], args.pages, cookie)
    links = collect_links(video["desc"], comments, args.all)

    # 输出结构化结果（agent 据此分析功能并测试工作流）
    print(json.dumps({
        "bvid": video["bvid"],
        "title": video["title"],
        "owner": video["owner"],
        "desc": video["desc"][:800],
        "comment_count_scanned": len(comments),
        "cookie_used": bool(cookie),
        "comment_coverage": "full" if cookie else "top-only(未登录仅能取到置顶/热评)",
        "workflow_links": links["links"],
        "note": "webappId 为空的链接需人工核对；任何 webappId 在 run 前必须 runninghub_app.py --info 验证",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
