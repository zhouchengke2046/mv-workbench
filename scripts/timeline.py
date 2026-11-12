#!/usr/bin/env python3
"""歌词时间轴骨架：量音频时长 + 按行均分，产出 时间轴.md（听感校准前的施工骨架）

用法：
  python3 timeline.py <歌词.md> <音频.mp3> [--out 02-音乐/时间轴.md]
  python3 timeline.py <歌词.md> --duration 45      # 没有音频时手工给秒数
超 12 字的行会警告（卡拉OK字幕一行放不下），[intro-*] 标记按 3s 前奏处理，
歌词文件以 `---` 分隔正文与元信息（韵脚/时长备注），分隔线之后不进时间轴。
"""
import argparse
import os
import re
import subprocess
import sys

from console import setup

setup()

MARK = re.compile(r"^\[(.+)\]\s*$")


def audio_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True)
        return float(out.stdout.strip())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lyrics")
    ap.add_argument("audio", nargs="?", help="mp3/wav/flac；缺省用 --duration")
    ap.add_argument("--duration", type=float, help="无音频时手工指定秒数")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    lines, intro = [], 0.0
    for raw in open(args.lyrics):
        s = raw.strip()
        if s == "---":  # 元信息分隔线：之后是韵脚/时长等备注，不是歌词
            break
        if not s or s.startswith(("#", ">")):
            continue
        m = MARK.match(s)
        if m:
            if m.group(1).startswith("intro"):
                intro = 3.0
            continue
        if len(s) > 12:
            print("[warn] 超12字建议拆行：%s" % s)
        lines.append(s)
    if not lines:
        sys.exit("[!] 歌词里没读到正文行（跳过空行/标记/#注释）")

    dur = (audio_duration(args.audio) if args.audio else None) or args.duration
    if not dur:
        sys.exit("[!] 给音频路径或 --duration 秒数")

    body = max(dur - intro, 1.0)
    per = body / len(lines)
    rows, t = [], intro
    for i, s in enumerate(lines, 1):
        rows.append((i, s, round(t, 1), round(t + per, 1)))
        t += per

    out = args.out
    if not out:
        base = os.path.dirname(os.path.abspath(args.lyrics))
        out = os.path.join(os.path.dirname(base), "02-音乐", "时间轴.md")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as f:
        f.write("# 时间轴（骨架 · 按行均分，需听感校准）\n\n")
        f.write("音源总长 %.1fs · 前奏 %.1fs · 正文 %d 行 ≈ %.1fs/行\n\n" % (dur, intro, len(lines), per))
        f.write("| # | 歌词 | 开始 | 结束 | 镜头 |\n|---|---|---|---|---|\n")
        for i, s, a, b in rows:
            f.write("| %d | %s | %.1f | %.1f | 镜%02d |\n" % (i, s, a, b, i))
    print("[ok] 骨架 -> %s（%d 行，总长 %.1fs）" % (out, len(lines), dur))
    print("提醒：均匀分配只是骨架；定稿前按听感逐句校准 start/end（改一句=分镜改一镜）")


if __name__ == "__main__":
    main()
