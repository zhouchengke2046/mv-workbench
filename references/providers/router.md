# Router / TokenTech（Muse / moss / ace）

## 连接

| 项 | 值 |
|---|---|
| Base URL | `https://router.kcacher.top` |
| API | `https://router.kcacher.top/v1` |
| 鉴权 | `Authorization: Bearer <router key>` |
| 面板 | `https://router.kcacher.top/keys` |
| 文档 | `https://router.kcacher.top/docs` |

> 不要用 `router.kbtech.app`（曾被阿里云 ICP 拦截）。用 `router.kcacher.top`。

## 任务协议（moss 生图 / ace 生音乐，2026-11-14 实测）

```text
POST /v1/responses                    # 提交（background:true 立即返回）
GET  /v1/responses/{response_id}      # 轮询 queued → in_progress → completed
GET  /v1/tasks/{task_id}/artifacts    # 产物清单
产物 URL 在 output 里 src="..."（带 ?access= 签名，需带 Bearer 下载）
```

提交体——**参数只认 `metadata.nodeInfoList`**（直通 RunningHub 工作流节点；有 nodeInfoList 时 `input` 不参与映射）：

```json
{
  "model": "moss-t2i-rh-ck",
  "input": "<主提示词>",
  "background": true,
  "metadata": {
    "nodeInfoList": [
      {"nodeId": "4",  "fieldName": "text",  "fieldValue": "<主提示词>"},
      {"nodeId": "5",  "fieldName": "text",  "fieldValue": "<负向词>"},
      {"nodeId": "16", "fieldName": "seed",  "fieldValue": 123}
    ]
  }
}
```

- moss-t2i-rh-ck：`4`=主提示词 text、`5`=负向 text、`16`=seed；单次返回 1 张竖版 PNG。
- ace-step-1.5-rh-ck：`114`=风格 text、`115`=歌词 text（[Verse]/[Chorus] 段落标记）、`116`=时长（秒，Float）、`117`=BPM、`94`=language/keyscale/timesignature（默认 zh / C major / 4，未单测）。
- 时长可控实测：116.value=60 → 成片 60.0s；不传则默认 180s。
- 鉴定手段：产物文件内嵌工作流快照（PNG tEXt / MP3 ID3 TXXX `prompt`），可直接核对节点实跑值。
- 计费：按 RH 实际运行时长扣费，单次金额浮动（实测 moss ¥0.31-0.37、ace ¥0.31-0.46），**以账单实扣为准**。
- 失败/超时走统一提醒：K001/P1/P2/P3/P4/P5/P6（platform=router）。

## 视频接口（含 R2V 参考图，2026-11-14 实测）

R2V 参考图通道：提交体加 `"image": "<URL>"`（单图）或 `"image_urls": ["<角色图>", "<场景图>"]`（多图），上游按参考图处理。实测配方：角色三视图 + 门头场景 → 人物跨段一致 + 品牌灯牌正确生成。费用仍按运行时长实扣（10s ≈ ¥0.17）。

## 视频接口

```text
POST /v1/videos
GET  /v1/videos/{id}
GET  /v1/videos/{id}/content
```

请求（文本生视频，2026-11-13 实测）：

```json
{
  "model": "muse-video-ext",
  "prompt": "竖屏 9:16，固定机位，夜晚街口，一个女生抬头看雨，电影感，环境声：细雨，无对白。",
  "seconds": 2,
  "resolution": "720p",
  "size": "720x1280"
}
```

- 2s 实测：2.000s / 720×1280 / 24fps / H.264 + AAC / 1.2MB。
- 计费：2s ≈ ¥1；10s ≈ ¥5；以账单为准。
- 参考图字段**尚未验证**；`image_urls` / `input_reference` / 单个 `image` 需要实测。400 校验失败不扣费，200 建任务才扣费。

## 余额

```text
GET /v1/dashboard/billing/subscription
GET /v1/dashboard/billing/usage
```

new-api 语义：`hard_limit_usd` 是总额度，`total_usage` 是已用（分），余额 = `hard_limit - total_usage/100`；`/api/status` 的 `quota_display_type` 决定币种（本中转站为 CNY）。

## 脚本

```bash
./mvwb muse --prompt "..." --seconds 2 --size 720x1280 --out out.mp4
```

或 `python3 scripts/mv_keys.py exec --need router -- python3 scripts/providers/tokentech_video.py ...`。

## 生图 / 生音乐脚本

```bash
python3 scripts/providers/tokentech_task.py image \
  --prompt "..." --negative "blurry, deformed, watermark" --seed 123 --out out.png
python3 scripts/providers/tokentech_task.py music \
  --lyrics "[Verse]...[Chorus]..." --style "female vocals, dream pop, 66 BPM" \
  --seconds 60 --bpm 66 --out out.mp3
```
