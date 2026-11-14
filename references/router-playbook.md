# Router 主链正确路径（playbook）

> 2026-11-14 端到端实测定稿（《半糖晚风》30s 全链 + 单项探针）。**生成一律走这条路径**；
> 备用链（RunningHub 直连 `mvwb rh` / APIMart）只在 B001 之后启用。
> 口径：**费用不做单价预估，账单实扣多少显示多少**（Router 按 RunningHub 实际运行时长计扣）。

## 0. 主链一览

| 能力 | 模型 | 端点 | 脚本 | 实扣参考 |
|---|---|---|---|---|
| 音乐 | `ace-step-1.5-rh-ck` | `POST /v1/responses` | `tokentech_task.py music` | ≈¥0.23/次（时长参数可控） |
| 资产图 | `moss-t2i-rh-ck` | `POST /v1/responses` | `tokentech_task.py image` | ≈¥0.23/张 |
| 视频段 | `muse-video-ext` | `POST /v1/videos` | `tokentech_video.py` | ≈¥0.17/10s 段 |
| 时间轴 | — | 本地 | `mvwb timeline` | 免费 |

四个任务的产物都是「任务受理 → 轮询 → 签名 URL 下载」，断连重试 2-4 次必成（P6 已接线）。

## 1. 音乐（ace）

```bash
python3 scripts/providers/tokentech_task.py music \
  --lyrics "<[Intro]/[Verse]/[Chorus] 结构化歌词，原文不改写>" \
  --style "<female soft vocals, warm city pop, ... 92 BPM, C major>" \
  --seconds 30 --bpm 92 --language zh --keyscale "C major" --timesignature 4 \
  --out MV001/01_music/song_v1.mp3
```

- 协议：`POST /v1/responses {model, input, background:true, metadata:{nodeInfoList:[…]}}`；
  **参数只认 nodeInfoList**：114=风格 text、115=歌词 text、116=时长秒 value、117=BPM value、
  94=language/keyscale/timesignature（默认 zh / C major / 4）。
- **时长精确可控**（116.value=30 → 30.0s 实证）；不传默认 180s。
- 自检：`ffprobe` 时长与目标差 ≤1s；ID3 TXXX `prompt` 快照里 114/115/116/117 应为本任务的值。
- 有 nodeInfoList 时 `input` 不映射歌词 —— 歌词必须写进 115 节点（脚本已处理）。
- 时间轴：`mvwb timeline 原文/lyric.json <mp3> --out MV001/01_music/timeline_v1.json`
  （json 进 json 出，骨架均分，听感校准后锁定）。

## 2. 资产图（moss）

```bash
python3 scripts/providers/tokentech_task.py image \
  --prompt "<含版式/锚点/文字政策的完整提示词>" \
  --negative "blurry, deformed hands, extra fingers, fused limbs, watermark, garbled text" \
  --seed <固定> --out MV001/02_assets/<name>_v1.png
```

- nodeInfoList：4=主提示词 text、5=负向 text、16=seed。
- 角色三视图模板（左格正面脸 / **中格全身但头完全不入画** / 右格背面）见
  `references/prompts/casting-style.md` §3 —— 中格出现脸 = Q1 fail 必须重跑。
- QA 门禁：`pass | warn | fail`；fail 必跑 v2，warn 用户确认后才用；版本不覆盖。
- 自检：PNG tEXt `prompt` 快照可核对节点实跑值（用唯一标记词归因）。

## 3. 视频段（muse，R2V 是默认，禁止人物镜头纯文生）

```bash
python3 scripts/providers/tokentech_video.py \
  --prompt "<按画面脚本的多镜头时间线提示词>" \
  --seconds 10 --size 720x1280 --resolution 720p \
  --image-urls "<角色三视图URL>" "<场景门头URL>" --image-field image_urls \
  --out MV001/03_segments/G1_v2.mp4
```

- **参考图通道实测生效**：`image`（单 URL）与 `image_urls`（数组）都按参考图处理。
- **标准配方 = 双图**：第 1 张角色三视图（人物锚定）+ 第 2 张主场景图（场景/品牌锚定）。
  实测：人物跨段一致、门头灯牌文字（品牌名）正确生成。
- 图源直接用中转站产物签名 URL（`*_meta/meta.json` 的 `artifact_url`，免鉴权可被上游拉取）。
- 自检：ffprobe 每段 ≤10s、720×1280、与段计划差 ≤0.5s（Q3）；**抽帧比对角色与三视图**
  （发型/服装/体型），明显不符 → 提示词补角色细节或换 seed 重跑 v2。
- 边界：脸型一致性是概率性的（参考图只是抬高概率）；构图/首帧锁定的进阶解法见「5. 备用与进阶」。

## 4. 对账与展示

- 每次生成后 `mvwb keys balance --data <data.json>`，把 **usage delta（实扣）** 写进
  `cost/spent` 与 `mv_manifest.json`，工作台右上角余额随 build 刷新。
- 报价（quote/fx.rh_coin）只是预算参考；**账单实扣优先**。

## 5. 备用与进阶

| 场景 | 路径 |
|---|---|
| Router 连续失败 | **B001** 提醒转发老师 → 老师发备用 zz-keys.json（RunningHub 直连 `mvwb rh` / APIMart） |
| 构图/首帧也要锁定 | 关键帧法：MOSS 按画面脚本出每段首帧 → 视频模型 i2v（muse R2V 传首帧图可试） |
| 一致性要求极高（主角大特写） | H3 多参模式：`minimax-h3-rh-ck` 同协议 nodeInfoList（155=index 2 多参、47/112…=参考图槽位），成本更高先测算；或 APIMart 的 Wan2.7-R2V / Vidu Q3 R2V |
| 生成完了还是不像 | 后期换脸兜底（比重生成便宜） |

## 6. 鉴定技巧（参数到底生效没有）

任务产物内嵌工作流快照：**PNG 看 tEXt `prompt`、MP3 看 ID3 TXXX `prompt`**，
里面是 ComfyUI 实跑 JSON。给每种传参形状塞唯一标记词（如 `STYLE_FROM_NODEINFO_…`），
再比对快照里的节点值即可归因 —— 不用靠听/看猜。
