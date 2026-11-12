# Router / TokenTech（Muse）

## 连接

| 项 | 值 |
|---|---|
| Base URL | `https://router.kcacher.top` |
| API | `https://router.kcacher.top/v1` |
| 鉴权 | `Authorization: Bearer <router key>` |
| 面板 | `https://router.kcacher.top/keys` |
| 文档 | `https://router.kcacher.top/docs` |

> 不要用 `router.kbtech.app`（曾被阿里云 ICP 拦截）。用 `router.kcacher.top`。

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
