# ACE-Step 1.5

## 模型事实（2026-11 实测）

| 项 | 值 |
|---|---|
| 工作流 | `2075301815628943362`（AI 应用） |
| 价格 | 39 币 / 45s |
| 节点 | `114:text` 风格标签、`115:text` 歌词、`116:value` 时长秒 |
| 备选 | YuE2 `2100804193576644610`，34 币/45s，输出略短 |
| 许可 | ACE-Step Apache-2.0，商用相对安全；YuE2 权重商用需确认 |

## 标签写法

英文逗号分隔，四类拼一起：

```
mandarin pop, bright female vocals, upbeat, clean electric guitar, city pop, warm
mandopop, gentle female vocals, slow ballad, piano and strings, emotional
```

- 曲风、人声、情绪/速度、乐器/质感各至少一个。
- 不要写自然语言长句；ACE 读标签，不读 H3/Muse 的结构化提示词。

## 歌词

- 保留甲方原文，只加结构标记：`[intro-short]`、`[verse]`、`[chorus]`、`[bridge]`、`[outro]`。
- 不拆行、不改字；时长用 `116:value` 秒数控制。
- 中文咬字优先 ACE；生成后试听：咬字、风格、速度/情绪、时长。

## 调用

```bash
mvwb rh --app 2075301815628943362 \
  --name song_v1 \
  --overrides <project>/02_music/ov_song_v1.json \
  --out <project>/02_music
```

overrides 示例：

```json
{
  "114:text": "mandarin pop, bright female vocals, upbeat, clean electric guitar, city pop, warm",
  "115:text": "[intro-short]\n[verse]\n...\n[chorus]\n...",
  "116:value": "45"
}
```

- 每次重跑都是一次新提交，都过报价门（39 币/次）。
- 生成后出逐句时间轴；视频段以真实音乐时间轴为准，不要用计划时长。
- 时间轴/对齐：`mvwb timeline`（只产时间轴，不切视频）。

详细节点与试听循环见 [`ace-step.md`](ace-step.md)。
