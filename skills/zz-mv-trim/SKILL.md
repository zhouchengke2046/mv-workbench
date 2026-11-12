---
name: zz-mv-trim
description: MV素材粗剪：把多镜头视频段按歌词时间轴切成"一句歌词一段"，输出trim_manifest、contact_sheet和报告，降低剪辑难度。当用户说"粗剪/素材处理/视频段对歌词/切镜头/trim/审片图/素材对不上歌词"，或MV工作台点"粗剪"按钮时使用。
---

# zz-mv-trim · MV 素材粗剪 v0.1

## 解决什么

视频模型一条 10s 往往含 2–3 个镜头，和音乐每句歌词对不齐。剪辑师要自己找镜头、对时间轴、裁切，50 人批量时这是最大的人工成本。

这个 skill 做三件事：

1. **对轴**：读 `timeline.json` 的每句起止秒，把每条素材切成“一句一段”，时长严格等于歌词；
2. **校正**：用 ffmpeg 场景检测找素材里的真实硬切，预期切点对不上时自动平移窗口；
3. **降门槛**：输出 `trim_manifest.json` + `contact_sheet.jpg`，剪辑师只看一张审片图，先审 high/medium/low，再决定换不换候选。

## 输入

| 文件 | 说明 |
|---|---|
| `timeline_v1.json` | 每句 `line_id/text/start/end`；时间是歌词段内相对时间 |
| `clip_manifest.json` | 每段素材 `source/duration/intended[]`；`intended` 是“预期覆盖哪句、素材内时间窗” |
| `media_root` | 素材根目录；`source` 是相对路径时用它拼 |
| 原始素材 | `raw/*.mp4`，只读，不被覆盖 |

契约定义见 `mv-factory/contracts/`。

## 输出

```
out/
├─ trim/L01.mp4 … L20.mp4    每句一段，视频only，保留素材分辨率
├─ trim_manifest.json        每句用了哪段的哪几秒 + 置信度/标记
├─ contact_sheet.jpg         20格审片图（歌词/时长/入点/置信度/标记）
└─ trim_report.md            人读报告 + 需人工复核清单
```

## 命令

```bash
mvwb trim \
  --timeline timeline_v1.json \
  --clips clip_manifest.json \
  --media-root /path/to/media \
  --out out/ \
  --threshold 0.15
```

常用参数：

- `--lines L01,L05`：只重跑指定句（换候选/修错时用）；
- `--fps 30`：输出统一 30fps；默认跟素材；
- `--crf 16 --preset veryfast`：画质/速度；
- `--no-contact-sheet`：批量跑时不生成审片图。

## 规则（写死，别让人临时发挥）

1. **一句一段，时长=歌词时长**；不冻结、不慢放、不硬凑。
2. **原始素材永不覆盖**；`trim/` 是派生文件，随时可重跑。
3. **预期切点只是先验**；以场景检测到的真实切点为准，允许 ±0.6s 平移。
4. **窗口内允许有硬切**，但必须标 `crosses_cut`；让剪辑师决定接受还是换候选。
5. **素材不够长**标 `coverage_short`，不自动拉伸；换候选或回视频阶段重生成。
6. **低置信度必须人审**；high 可以批量过。
7. **粗剪只出视频轨**，不挂音乐、不烧字幕；音乐和字幕在装配阶段统一处理。

## 置信度

| 级别 | 条件 | 处理 |
|---|---|---|
| `high` | 偏移≤0.12s 且窗口内0个硬切 | 可批量通过 |
| `medium` | 偏移≤0.60s 且窗口内≤1个硬切 | 看审片图，必要时换候选 |
| `low` | 偏移>0.60s / 多个硬切 / 素材不够长 / 无映射 | 必须人审或重生成 |

标记：

- `shifted`：为避开硬切，窗口相对预期平移了 >0.12s；
- `crosses_cut`：窗口内含硬切；
- `coverage_short`：素材比歌词短；
- `missing_media`：素材文件不存在；
- `low_confidence`：综合低置信度。

## 与工作台集成

工作台“视频”阶段卡上的“粗剪”按钮，等价于：

1. 读该 MV 的 `timeline_v1.json` + `clip_manifest.json`；
2. 调 `trim.py`，输出到 `MV001/04_clips/trim/`；
3. 把 `trim_manifest.json` 的 `summary` 回填到 MV 状态；
4. 在 UI 里展示 `contact_sheet.jpg`，按 confidence 过滤。

不要把 trim 逻辑写进前端；前端只调脚本、读 manifest。

## 当前限制

- 只做**时间/切点对齐**，不做语义匹配。镜头内容对不对，仍要看审片图；后续可加 CLIP/VLM 只对 low 置信度做二次判断。
- 场景检测用 ffmpeg `scene` 分数，软过渡/快速运镜可能漏检或误检；阈值默认 0.15，可按素材调。
- 输出保留素材 fps；最终 30fps 归一化在装配阶段做，最后一段按总时长补帧。
- 多候选素材会自动选评分最高的；如果两条候选都差，标 low，回视频阶段重生成。

## 文件

```
zz-mv-trim/
├─ SKILL.md
├─ references/trim-rules.md
└─ scripts/
   ├─ trim.py                 主流程
```

已在 20 句样本上验证：12 high / 8 medium / 0 low；仓库不附客户素材。
