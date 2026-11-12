#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图片提示词房屋口径机检。
用法: python3 check_image_prompts.py <图片提示词.md> [--json]
门: 每条 IMG 双 text 块(zh→en) / 段标签齐全 / 角色三视图 / 道具多视图 / 场景空镜大全景45° / 负面非空。
exit 0 = PASS; 1 = FAIL。
"""
import json, re, sys
from pathlib import Path

from console import setup

setup()

CORE = ["用途", "画风", "版式", "背景", "文字政策", "负面"]
GROUP = {
    "C": {"must": ["三视图|三格", "面部特写", "头部完全|无头", "背面", "纯色|无缝"], "extra": ["身份锚点", "姿态"]},
    "S": {"must": ["无人|空镜", "大全景", "45|俯视|俯拍"], "extra": ["地理锚点", "光线|布光"]},
    "P": {"must": ["多视图|正/侧|正、侧|正视图", "纯色|无缝"], "extra": ["结构锚点", "光线|布光"]},
    "D": {"must": ["特写|微距"], "extra": ["结构锚点", "光线|布光"]},
}

def check(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    items = re.findall(r"### (IMG-[A-Z]\d+)[ 　]*(.*?)\n(.*?)(?=### IMG-|\Z)", text, re.S)
    results, ok_all = [], True
    if not items:
        return [{"id": "—", "pass": False, "issues": ["未找到任何 ### IMG-* 条目"]}], False
    for img_id, title, body in items:
        issues = []
        blocks = re.findall(r"```text\n(.*?)```", body, re.S)
        if len(blocks) != 2:
            issues.append(f"应恰好 2 个 text 块(zh+en),实际 {len(blocks)}")
        labels_zh = set(re.findall(r"【([^】]+)】", blocks[0])) if blocks else set()
        for lab in CORE:
            if lab not in labels_zh:
                issues.append(f"zh 缺段【{lab}】")
        grp = img_id[4]
        g = GROUP.get(grp)
        if not g:
            issues.append(f"未知组前缀 {img_id}")
        else:
            for lab in g["extra"]:
                if not any(re.search(lab, l) for l in labels_zh):
                    issues.append(f"zh 缺段【{lab}】")
            for pat in g["must"]:
                if not re.search(pat, blocks[0] if blocks else ""):
                    issues.append(f"正文缺版式关键词: /{pat}/")
        if blocks:
            m = re.search(r"【负面】(.*?)(?:\n|$)", blocks[0].replace("】\n", "】"))
            neg = m.group(1) if m else ""
            if len(neg.strip()) < 15:
                issues.append("【负面】过短(<15字),四类负向未覆盖")
            if blocks[-1].strip() and not re.search(r"Negative|负面|不要|no\b", blocks[-1], re.I):
                issues.append("en 块疑似缺负面段")
        results.append({"id": img_id, "name": title.strip(), "pass": not issues, "issues": issues})
        ok_all = ok_all and not issues
    return results, ok_all

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法: python3 check_image_prompts.py <图片提示词.md> [--json]"); sys.exit(2)
    results, ok = check(args[0])
    if "--json" in sys.argv:
        print(json.dumps({"pass": ok, "items": results}, ensure_ascii=False, indent=1))
    else:
        for r in results:
            print(("PASS " if r["pass"] else "FAIL ") + r["id"] + " " + r.get("name", ""))
            for i in r["issues"]:
                print("   - " + i)
        n = sum(1 for r in results if r["pass"])
        print(f"— 共 {len(results)} 条: PASS {n} / FAIL {len(results)-n}")
    sys.exit(0 if ok else 1)
