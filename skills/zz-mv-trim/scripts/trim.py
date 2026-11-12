#!/usr/bin/env python3
"""zz-mv-trim · MV 素材粗剪

把多镜头视频段按歌词时间轴切成“一句歌词一段”，降低剪辑难度。

输入:
  timeline_v1.json     每句歌词的 start/end（歌词段内相对时间）
  clip_manifest.json   每段素材预期覆盖哪些句、素材内时间窗
  media_root           素材根目录

输出:
  out/trim/L01.mp4 ...       每句一段，时长=歌词时长
  out/trim_manifest.json     每句用了哪段素材的哪几秒 + 置信度/标记
  out/contact_sheet.jpg      20格缩略图审片图
  out/trim_report.md         人读报告

用法:
  python3 trim.py --timeline timeline_v1.json --clips clip_manifest.json \
      --media-root /path/to/media --out out/
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- 基础工具

PROBE_CACHE = {}
CUTS_CACHE = {}


def run(cmd, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError("命令失败:\n%s\n%s" % (" ".join(cmd), p.stderr[-1200:]))
    return p


def probe(path):
    path = os.path.abspath(path)
    if path in PROBE_CACHE:
        return PROBE_CACHE[path]
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
           "-show_entries", "format=duration", "-of", "json", path]
    d = json.loads(run(cmd).stdout)
    st = d["streams"][0]
    num, den = (st.get("r_frame_rate") or "24/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(st.get("duration") or d["format"].get("duration") or 0)
    info = {"duration": dur, "fps": fps, "width": st["width"],
            "height": st["height"], "nb_frames": st.get("nb_frames")}
    PROBE_CACHE[path] = info
    return info


def detect_cuts(path, threshold=0.15, min_gap=0.25, edge_eps=0.08):
    """用 ffmpeg 的 scene 分数检测硬切；返回素材内的切点秒数（不含首尾）。"""
    path = os.path.abspath(path)
    key = (path, threshold)
    if key in CUTS_CACHE:
        return CUTS_CACHE[key]
    vf = "select='gt(scene,%s)',metadata=print:file=-" % threshold
    p = run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf,
             "-an", "-f", "null", "-"], check=False)
    times = [float(m.group(1)) for m in re.finditer(r"pts_time:([0-9.]+)", p.stdout)]
    times.sort()
    cuts = []
    for t in times:
        if not cuts or t - cuts[-1] >= min_gap:
            cuts.append(t)
    dur = probe(path)["duration"]
    cuts = [round(t, 3) for t in cuts if edge_eps < t < dur - edge_eps]
    CUTS_CACHE[key] = cuts
    return cuts


def resolve(src, media_root):
    if not src:
        return ""
    return src if os.path.isabs(src) else os.path.normpath(os.path.join(media_root, src))


# ---------------------------------------------------------------- 契约读取

def load_timeline(path):
    d = json.load(open(path, encoding="utf-8"))
    lines = d.get("lines")
    if not lines:
        # 兼容 legacy muse版 timeline.json: shots[{clip,in,dur,line}]
        lines, t = [], 0.0
        for i, s in enumerate(d.get("shots", []), 1):
            dur = float(s["dur"])
            lines.append({"line_id": "L%02d" % i, "text": s["line"],
                          "start": round(t, 3), "end": round(t + dur, 3),
                          "confidence": 1.0})
            t += dur
        d["duration"] = d.get("total", t)
    for ln in lines:
        ln["start"] = float(ln["start"])
        ln["end"] = float(ln["end"])
        ln["duration"] = round(ln["end"] - ln["start"], 3)
        if ln["duration"] <= 0:
            raise ValueError("line %s 时长非正: %s" % (ln.get("line_id"), ln))
    d["lines"] = lines
    return d


def load_clips(path, timeline, media_root):
    d = json.load(open(path, encoding="utf-8"))
    clips = d.get("clips") if isinstance(d, dict) else d
    if not clips:
        raise ValueError("clip_manifest 没有 clips")
    line_ids = [ln["line_id"] for ln in timeline["lines"]]
    idx = 0
    out = []
    for c in clips:
        # 兼容 legacy clips.json: tag/out/shots
        if "clip_id" not in c:
            c = {
                "clip_id": c.get("tag"),
                "source": c.get("out"),
                "shots": c.get("shots", []),
                "prompt": c.get("prompt", ""),
            }
        src = resolve(c.get("source", ""), media_root)
        info = probe(src) if os.path.exists(src) else {"duration": 0, "fps": 24, "width": 0, "height": 0}
        intended = c.get("intended")
        if not intended:
            intended = []
            for s in c.get("shots", []):
                if idx >= len(line_ids):
                    break
                intended.append({"line_id": line_ids[idx],
                                 "start": float(s.get("start", 0)),
                                 "end": float(s.get("start", 0)) + float(s.get("dur", 0))})
                idx += 1
        out.append({
            "clip_id": c.get("clip_id") or os.path.basename(src),
            "source": c.get("source", ""),
            "src_abs": src,
            "duration": float(c.get("duration") or info["duration"]),
            "fps": float(c.get("fps") or info["fps"] or 24),
            "resolution": c.get("resolution") or ("%dx%d" % (info["width"], info["height"])),
            "intended": intended,
            "prompt": c.get("prompt", ""),
            "cost": c.get("cost"),
        })
    return out


# ---------------------------------------------------------------- 选窗算法

def best_window(clip_duration, intended_start, need, cuts, eps=0.12):
    """在素材里找一个长度为 need 的窗口。

    评分 = 相对预期入点的偏移 + 0.5×窗口内硬切数。
    候选起点 = 预期入点 / 0 / 末尾 / 每个切点 / 每个切点-need。
    """
    if need >= clip_duration:
        inside = sum(1 for c in cuts if eps < c < clip_duration - eps)
        return 0.0, inside, abs(intended_start), 1000.0 + abs(intended_start)

    max_start = clip_duration - need
    want = min(max(intended_start, 0.0), max_start)
    starts = {0.0, round(max_start, 3), round(want, 3)}
    for c in cuts:
        for w in (c, c - need):
            if 0.0 <= w <= max_start:
                starts.add(round(w, 3))

    best = None
    for w in sorted(starts):
        inside = sum(1 for c in cuts if w + eps < c < w + need - eps)
        shift = abs(w - want)
        score = shift + 0.5 * inside
        if best is None or score < best[3]:
            best = (w, inside, shift, score)
    return best


def choose_trim(line, clips, threshold):
    """在全部候选素材里，为一句歌词选最佳窗口。"""
    need = line["duration"]
    candidates = []
    for c in clips:
        for it in c.get("intended", []):
            if it["line_id"] != line["line_id"]:
                continue
            if not c["src_abs"] or not os.path.exists(c["src_abs"]):
                candidates.append((9999, c, it, 0.0, 0, need, ["missing_media"]))
                continue
            cuts = detect_cuts(c["src_abs"], threshold=threshold)
            w, inside, shift, score = best_window(c["duration"], float(it["start"]), need, cuts)
            flags = []
            if need > c["duration"] + 0.01:
                flags.append("coverage_short")
            if shift > 0.12:
                flags.append("shifted")
            if inside > 0:
                flags.append("crosses_cut")
            candidates.append((score, c, it, w, inside, shift, flags))

    if not candidates:
        return None

    score, c, it, w, inside, shift, flags = min(candidates, key=lambda x: x[0])

    if "coverage_short" in flags:
        conf = "low"
    elif shift <= 0.12 and inside == 0:
        conf = "high"
    elif shift <= 0.60 and inside <= 1:
        conf = "medium"
    else:
        conf = "low"
    if conf == "low":
        flags.append("low_confidence")

    return {
        "line_id": line["line_id"],
        "text": line["text"],
        "clip_id": c["clip_id"],
        "source": c["source"],
        "src_abs": c["src_abs"],
        "source_in": round(w, 3),
        "source_out": round(min(w + need, c["duration"]), 3),
        "duration": round(need, 3),
        "confidence": conf,
        "method": "intended+scene" if detect_cuts(c["src_abs"], threshold) else "intended",
        "shift": round(shift, 3),
        "cuts_inside": inside,
        "flags": sorted(set(flags)),
        "clip_duration": c["duration"],
        "clip_fps": c["fps"],
    }


# ---------------------------------------------------------------- 切素材

def cut_clip(src, out, start, duration, fps=None, crf=16, preset="veryfast"):
    info = probe(src)
    out_fps = float(fps or info["fps"] or 24)
    nframes = max(1, int(round(duration * out_fps)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-ss", "%.3f" % start,
           "-t", "%.3f" % duration, "-frames:v", str(nframes), "-an",
           "-vf", "fps=%s,setsar=1" % out_fps,
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", out]
    run(cmd)
    actual = probe(out)["duration"]
    if abs(actual - duration) > 1.6 / out_fps:
        print("[warn] %s 输出 %.3fs，目标 %.3fs" % (os.path.basename(out), actual, duration))


# ---------------------------------------------------------------- 审片图

def _font(size):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Medium.ttc",
              "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"):
        if os.path.exists(p):
            for idx in (0, 1):
                try:
                    return ImageFont.truetype(p, size, index=idx)
                except Exception:
                    continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width, max_lines=2):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= max_width:
            cur += ch
        else:
            if cur:
                lines.append(cur)
            cur = ch
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len("".join(lines)) < len(text):
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def make_contact_sheet(trims, out_path, mv_id, cols=4):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    if not trims:
        return
    margin, gap = 18, 12
    cell_w, img_h, text_h = 300, 533, 128
    rows = math.ceil(len(trims) / cols)
    header = 58
    W = margin * 2 + cols * cell_w + (cols - 1) * gap
    H = header + margin + rows * (img_h + text_h + gap)
    sheet = Image.new("RGB", (W, H), (17, 19, 24))
    draw = ImageDraw.Draw(sheet)
    f_title = _font(22)
    f_small = _font(14)
    f_line = _font(16)
    f_tiny = _font(12)
    conf_color = {"high": (63, 185, 111), "medium": (224, 166, 63), "low": (226, 90, 90)}

    draw.text((margin, 18), "%s · 粗剪审片图" % mv_id, font=f_title, fill=(232, 234, 240))
    counts = {k: sum(1 for t in trims if t["confidence"] == k) for k in ("high", "medium", "low")}
    draw.text((margin + 260, 24),
              "high %d  ·  medium %d  ·  low %d" % (counts["high"], counts["medium"], counts["low"]),
              font=f_small, fill=(139, 144, 160))

    tmp = tempfile.mkdtemp(prefix="mvtrim_")
    try:
        for i, t in enumerate(trims):
            r, c = divmod(i, cols)
            x = margin + c * (cell_w + gap)
            y = header + r * (img_h + text_h + gap)
            draw.rounded_rectangle([x, y, x + cell_w, y + img_h + text_h],
                                   radius=8, fill=(26, 29, 36), outline=(42, 46, 56))
            frame = os.path.join(tmp, "%s.jpg" % t["line_id"])
            frame_src = t.get("_abs_path") or t.get("path")
            if frame_src and os.path.exists(frame_src):
                run(["ffmpeg", "-v", "error", "-ss", "%.3f" % min(0.6, t["duration"] * 0.45),
                     "-i", frame_src, "-frames:v", "1", "-q:v", "3", "-y", frame], check=False)
            if os.path.exists(frame):
                im = Image.open(frame).convert("RGB")
                im = ImageOps.fit(im, (cell_w, img_h), method=Image.LANCZOS)
                sheet.paste(im, (x, y))
            else:
                draw.rectangle([x, y, x + cell_w, y + img_h], fill=(30, 33, 40))
                draw.text((x + 20, y + img_h // 2), "无素材", font=f_line, fill=(139, 144, 160))

            col = conf_color.get(t["confidence"], (139, 144, 160))
            draw.rectangle([x, y, x + 5, y + img_h + text_h], fill=col)
            draw.text((x + 12, y + img_h + 8), "%s  %s" % (t["line_id"], t["confidence"].upper()),
                      font=f_small, fill=col)
            draw.text((x + 12, y + img_h + 28), "%.2fs  in %.2f" % (t["duration"], t["source_in"]),
                      font=f_tiny, fill=(139, 144, 160))
            lines = wrap_text(draw, t["text"], f_line, cell_w - 24)
            for k, ln in enumerate(lines):
                draw.text((x + 12, y + img_h + 48 + k * 20), ln, font=f_line, fill=(232, 234, 240))
            if t["flags"]:
                draw.text((x + 12, y + img_h + 100), " · ".join(t["flags"])[:34],
                          font=f_tiny, fill=(224, 166, 63))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    sheet.save(out_path, quality=90)
    print("[ok] 审片图 %s（%d 格）" % (out_path, len(trims)))


# ---------------------------------------------------------------- 报告

def write_report(trims, missing, timeline, out_path, mv_id):
    counts = {k: sum(1 for t in trims if t["confidence"] == k) for k in ("high", "medium", "low")}
    cross = sum(1 for t in trims if t["cuts_inside"] > 0)
    lines = [
        "# %s 粗剪报告" % mv_id,
        "",
        "- 歌词段: %.2fs（前奏 %.2fs）" % (timeline.get("duration", 0), timeline.get("intro", 0)),
        "- 完成: %d 句 / 缺失: %d" % (len(trims), len(missing)),
        "- 置信度: high %d / medium %d / low %d" % (counts["high"], counts["medium"], counts["low"]),
        "- 窗口内含硬切: %d 句（剪辑时可换候选或接受）" % cross,
        "",
        "| 句 | 歌词 | 素材 | 入点 | 出点 | 时长 | 置信度 | 偏移 | 标记 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in trims:
        lines.append("| %s | %s | %s | %.2f | %.2f | %.2f | %s | %+.2f | %s |" % (
            t["line_id"], t["text"], t["clip_id"], t["source_in"], t["source_out"],
            t["duration"], t["confidence"], t["shift"], ", ".join(t["flags"]) or "-"))
    if missing:
        lines += ["", "## 缺失", ""]
        for m in missing:
            lines.append("- %s %s：%s" % (m["line_id"], m.get("text", ""), m["reason"]))
    review = [t for t in trims if t["confidence"] != "high" or t["cuts_inside"]]
    if review:
        lines += ["", "## 需人工复核", ""]
        for t in review:
            lines.append("- %s %s：%s（偏移 %+.2fs，窗口内 %d 个切点）" % (
                t["line_id"], t["text"], t["confidence"], t["shift"], t["cuts_inside"]))
    open(out_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("[ok] 报告 %s" % out_path)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="MV 素材粗剪：一句歌词一段")
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--media-root", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=None, help="输出帧率；默认跟素材")
    ap.add_argument("--threshold", type=float, default=0.15, help="场景检测阈值，默认0.15")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--lines", default=None, help="只处理这些句，逗号分隔，如 L01,L02")
    ap.add_argument("--no-contact-sheet", action="store_true")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out)
    trim_dir = os.path.join(out_dir, "trim")
    os.makedirs(trim_dir, exist_ok=True)

    timeline = load_timeline(os.path.abspath(args.timeline))
    media_root = args.media_root or timeline.get("media_root") or ""
    clip_doc = json.load(open(os.path.abspath(args.clips), encoding="utf-8"))
    media_root = media_root or (clip_doc.get("media_root") if isinstance(clip_doc, dict) else "")
    clips = load_clips(os.path.abspath(args.clips), timeline, media_root)

    only = set(x.strip() for x in args.lines.split(",")) if args.lines else None
    mp = os.path.join(out_dir, "trim_manifest.json")
    old = None
    if only and os.path.exists(mp):
        try:
            old = json.load(open(mp, encoding="utf-8"))
            for t in old.get("trims", []):
                if t.get("path"):
                    t["_abs_path"] = os.path.join(out_dir, t["path"])
        except Exception as e:
            print("[warn] 旧 manifest 读不了，按全量重写: %s" % e)
            old = None
    trims, missing = [], []
    for line in timeline["lines"]:
        if only and line["line_id"] not in only:
            continue
        t = choose_trim(line, clips, args.threshold)
        if not t:
            missing.append({"line_id": line["line_id"], "text": line["text"],
                            "reason": "no_intended_clip"})
            print("[missing] %s %s" % (line["line_id"], line["text"]))
            continue
        if "missing_media" in t["flags"]:
            missing.append({"line_id": line["line_id"], "text": line["text"],
                            "reason": "missing_media: %s" % t["source"]})
            continue
        out_path = os.path.join(trim_dir, "%s.mp4" % line["line_id"])
        cut_clip(t["src_abs"], out_path, t["source_in"], t["duration"],
                 fps=args.fps, crf=args.crf, preset=args.preset)
        info = probe(out_path)
        t["_abs_path"] = out_path
        t["path"] = os.path.relpath(out_path, out_dir)
        t["actual_duration"] = round(info["duration"], 3)
        t["frames"] = int(round(info["duration"] * info["fps"]))
        t["fps"] = info["fps"]
        trims.append(t)
        print("[ok] %s %-6s %s in=%.2f out=%.2f %.2fs%s" % (
            line["line_id"], t["confidence"], t["clip_id"], t["source_in"],
            t["source_out"], t["duration"],
            ("  " + ",".join(t["flags"])) if t["flags"] else ""))

    if old:
        merged = {t["line_id"]: t for t in old.get("trims", [])}
        merged.update({t["line_id"]: t for t in trims})
        trims = [merged[k] for k in sorted(merged)]
        old_missing = {m["line_id"]: m for m in old.get("missing", [])}
        for lid in only:
            old_missing.pop(lid, None)
        for m in missing:
            old_missing[m["line_id"]] = m
        missing = [old_missing[k] for k in sorted(old_missing)]

    manifest = {
        "mv_id": timeline.get("mv_id", ""),
        "source_timeline": os.path.abspath(args.timeline),
        "source_clips": os.path.abspath(args.clips),
        "media_root": media_root,
        "fps": args.fps or (trims[0].get("fps") if trims else None),
        "summary": {
            "total": len(trims) + len(missing),
            "high": sum(1 for t in trims if t["confidence"] == "high"),
            "medium": sum(1 for t in trims if t["confidence"] == "medium"),
            "low": sum(1 for t in trims if t["confidence"] == "low"),
            "missing": len(missing),
            "cuts_inside": sum(1 for t in trims if t["cuts_inside"] > 0),
        },
        "trims": [{k: v for k, v in t.items()
                   if k not in ("src_abs", "clip_duration", "clip_fps", "_abs_path")}
                  for t in trims],
        "missing": missing,
    }
    mp = os.path.join(out_dir, "trim_manifest.json")
    json.dump(manifest, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[ok] manifest %s" % mp)

    write_report(trims, missing, timeline, os.path.join(out_dir, "trim_report.md"),
                 timeline.get("mv_id", "MV"))
    if not args.no_contact_sheet:
        make_contact_sheet(trims, os.path.join(out_dir, "contact_sheet.jpg"),
                           timeline.get("mv_id", "MV"))

    print("\n[summary] %d/%d 句完成，high %d / medium %d / low %d，缺 %d"
          % (len(trims), len(trims) + len(missing),
             manifest["summary"]["high"], manifest["summary"]["medium"],
             manifest["summary"]["low"], len(missing)))


if __name__ == "__main__":
    main()
