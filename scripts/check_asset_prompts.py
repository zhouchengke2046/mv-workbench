#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资产图提示词机检（moss.md 固定范式的门）。

用法：python3 scripts/check_asset_prompts.py 图片提示词.md [--json]
门（exit 0 才交付）：每条 IMG-* 双块 ✓ 九段标签齐全 ✓ 角色三视图关键词 ✓
道具纯底单视图 ✓ 场景无人+光向 ✓ 负面非空 ✓。
"""
import argparse
import json
import re
import sys

ZH_SECTIONS = ["用途", "画风", "版式", "锚点", "背景", "布光", "文字政策", "负面"]
EN_SECTIONS = ["Purpose", "Style", "Layout", "Anchors", "Background", "Lighting", "Text policy", "Negative"]
ZH_POSE = "姿态"
EN_POSE = "Pose"


def parse_entries(text):
    """按 IMG-* 标题切条目，返回 [(id, kind, body)]。"""
    parts = re.split(r"^#{2,4}\s*(IMG-[CSP]\d+[^\n]*)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        title, body = parts[i], parts[i + 1]
        kind = title[4]
        out.append((title.split()[0], kind, body))
    return out


def blocks(body):
    """取 zh/en 两个 ```text 块。"""
    chunks = re.findall(r"####\s*(zh|en)\s*\n+```text\n(.*?)```", body, flags=re.S)
    return {lang: code for lang, code in chunks}


def check_entry(eid, kind, body):
    errs = []
    bl = blocks(body)
    if "zh" not in bl or "en" not in bl:
        return ["%s: 缺 zh/en 双块（各有且仅有一个 ```text 块）" % eid]
    for lang, code in (("zh", bl["zh"]), ("en", bl["en"])):
        secs = ZH_SECTIONS if lang == "zh" else EN_SECTIONS
        pose_tags = (["姿态", "状态"] if lang == "zh" else ["Pose", "State"])
        for tag in secs[:4] + secs[4:]:
            if ("【%s】" % tag) not in code and ("[%s]" % tag) not in code:
                errs.append("%s %s: 缺段落【%s】" % (eid, lang, tag))
        if not any(("【%s】" % t) in code or ("[%s]" % t) in code for t in pose_tags):
            errs.append("%s %s: 缺段落【姿态/状态】" % (eid, lang))
        neg = re.search(r"(【负面】|\[Negative\])\s*\n?(.+)", code)
        if not neg or not neg.group(2).strip():
            errs.append("%s %s: 负面段为空" % (eid, lang))
    zh = bl["zh"]
    if kind == "C":
        for kw in ("三格", "三视图"):
            if kw not in zh:
                errs.append("%s zh: 角色三视图缺关键词「%s」" % (eid, kw))
        if "不入画" not in zh:
            errs.append("%s zh: 缺「头部完全不入画」约束" % eid)
        if "背面" not in zh:
            errs.append("%s zh: 缺背面全身格" % eid)
        if "四视图" not in zh:
            errs.append("%s zh: 缺「不要四视图」版式负向" % eid)
    if kind == "P":
        if "纯色" not in zh and "纯底" not in zh:
            errs.append("%s zh: 道具缺纯色/纯底背景" % eid)
        if "无手" not in zh:
            errs.append("%s zh: 道具缺「无手」约束" % eid)
    if kind == "S":
        if "无人" not in zh:
            errs.append("%s zh: 场景缺「无人」约束" % eid)
        if "大全景" not in zh and "固定机位" not in zh:
            errs.append("%s zh: 场景缺景别（大全景/固定机位）" % eid)
        if "光" not in zh:
            errs.append("%s zh: 场景缺光向描述" % eid)
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = open(args.file, encoding="utf-8").read()
    entries = parse_entries(text)
    errs = []
    if not entries:
        errs.append("没有找到任何 IMG-<C|S|P>nn 条目")
    for eid, kind, body in entries:
        errs += check_entry(eid, kind, body)
    if args.json:
        print(json.dumps({"ok": not errs, "entries": len(entries), "errors": errs},
                         ensure_ascii=False, indent=1))
    else:
        for e in errs:
            print("[fail] " + e)
        print("%s：%d 条提示词，%d 个问题" % ("通过" if not errs else "未通过", len(entries), len(errs)))
    sys.exit(0 if not errs else 1)


if __name__ == "__main__":
    main()
