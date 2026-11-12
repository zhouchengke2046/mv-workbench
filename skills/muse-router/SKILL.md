---
name: muse-router
description: Muse Video（muse-video-ext）通过 Router/TokenTech new-api 的提示词与调用规范：/v1/videos 异步任务、2-10s、720p、原生音频、参考图；含自然语言提示词指南。当用户说 Muse、muse-video-ext、Router 视频、10 秒多镜头、参考图生视频时使用。
---

# muse-router · Muse Video via Router

> APIMart 已从本仓库移除；统一走 Router（TokenTech/new-api）。模型仍是 `muse-video-ext`，提示词规则沿用 Muse 实测指南。

## 模型事实（2026-11-13 实测）

| 项 | 值 |
|---|---|
| API | `POST https://router.kcacher.top/v1/videos` |
| 轮询 | `GET /v1/videos/{id}` |
| 下载 | `GET /v1/videos/{id}/content` |
| 鉴权 | `Authorization: Bearer <router key>`；`/v1` 不接受登录会话令牌 |
| 输出 | 720p（720×1280 竖屏）/ 24fps / H.264 + AAC；2s 已实测 |
| 时长 | `seconds` 2–10；2s 实测成功，10s 未实测 |
| 价格 | 2s ≈ ¥1.00；10s ≈ ¥5.00（按 `/api/pricing` 的 USD 表达式 × 7.3） |
| 参考图 | Muse 原生最多 9 张；Router 的参考图字段**尚未验证**（`image_urls` / `input_reference` / 单个 `image`） |

## 调用

```bash
# 已配置 Router key 后
mvwb muse --prompt "竖屏 9:16，固定机位，夜晚街口，一个女生抬头看雨，电影感，环境声：细雨，无对白。" \
  --seconds 2 --size 720x1280 --out out/demo.mp4
```

或直接：

```bash
python3 scripts/mv_keys.py exec --need router -- python3 scripts/providers/tokentech_video.py \
  --prompt "..." --seconds 2 --size 720x1280 --out out/demo.mp4
```

请求体（文本生视频，已实测）：

```json
{
  "model": "muse-video-ext",
  "prompt": "...",
  "seconds": 2,
  "resolution": "720p",
  "size": "720x1280"
}
```

- 返回 `{"id":"task_...","status":"queued"}`；轮询到 `completed` 后下载 `/content`。
- 400 校验失败不扣费；200 建任务才扣费，所以不要一次堆很多未验证字段。
- 参考图：先用 1 张图做 2s 测试，确认字段后再批量；如果 Router 只支持单图，多参考图改用 H3/其他模型。

## 提示词

按顺序写一段自然语言（60–350 字）：

1. 主体锚定：图1是谁、不可变特征（与参考图逐字一致）
2. 动作：一个主线动作，按时间顺序
3. 镜头：景别 + 固定机位/轻微手持
4. 光线：光源、色温、时间
5. 声音：环境声 / 对白 / 音效（原生音频）
6. 文字处理：招牌、屏幕、旗帜上的字失焦虚化

- **固定机位优先**；10s 内“轻微推镜”容易跑飞。
- 不写 `subject_definitions`/`retention_analysis`/毫秒时间码；Muse 会当正文读。
- 否定句基本无效；用正向描述（柔和散射光、中性白平衡、低饱和）。
- 外貌描述必须与参考图一致：图里长发就不要写披肩发。
- 内容审核可能拦亲密/医疗/暴力动作；改成非接触动作。

完整规则：

- [`references/prompting.md`](references/prompting.md)
- [`references/muse_video_prompt_guide.md`](references/muse_video_prompt_guide.md)

## 成本门

- 2s ≈ ¥1；10s ≈ ¥5；生成前先 `mvwb quote --model muse-video-ext --seconds N`。
- 余额在 `mvwb doctor --network` 或工作台右上角查看。
- 失败/超时是否扣费以 Router 账单为准；批量前先报总价。
