# 步骤 2 · 音乐（基于定稿歌词）

产线（2026-11-06 实测，基于 2026-11 实测）：

| 产线 | 形态 | ID | 价 | 特点 |
|---|---|---|---|---|
| **ace-step 1.5（默认）** | AI 应用 | `2075301815628943362` | 39币/45s | 中文咬字清晰、时长精确、53s 出片、Apache-2.0 商用安全 |
| YuE2（备选） | AI 应用 | `2100804193576644610` | 34币/45s | 输出略短于设定 |

Suno/Mureka 已实测故障（第三方 key 缺失），不要试。

## 调用（节点已实测，不用重新探）

| 工作流 | 节点 |
|---|---|
| ace-step | `114:text`=风格标签（英文）、`115:text`=歌词全文（带结构标记）、`116:value`=时长秒 |
| YuE2 | `54:value`=风格标签、`55:value`=歌词、`56:value`=时长秒 |

```bash
# 1. 写 overrides（键格式 节点:字段）
# {"114:text": "mandarin pop, bright female vocals, upbeat", "115:text": "[intro-short]...", "116:value": "45"}
# 2. 过报价门后跑
mvwb rh --app 2075301815628943362 \
  --name 歌曲v1 --overrides <项目>/02-音乐/ov_歌曲v1.json --out <项目>/02-音乐
```

每次重跑都是一次新提交，都过报价门。

## 风格标签写法（114）

英文逗号分隔，四类拼一起：`<曲风>, <人声>, <情绪/速度>, <乐器/质感>`

```
mandarin pop, bright female vocals, upbeat, clean electric guitar, city pop, warm
mandopop, gentle female vocals, slow ballad, piano and strings, emotional
```

## 试听循环

1. 生成完报文件路径，请用户听（或开 workbench.html）
2. 反馈分类处理：
   - 咬字不清 → 改歌词里拗口的词（回歌词步局部改），或跑 YuE2 对照
   - 风格不对 → 改 114 标签重跑
   - 速度/情绪不对 → 114 加 tempo/emotion 词
   - 时长不对 → 116 调秒数（ace-step 时长精确）
3. `versions[]` note 记一句原因；定稿 `final`+`engine`

## 定稿后：时间轴（分镜施工图）

定稿后**必须**产出 `02-音乐/时间轴.md`——每句歌词起止秒，画面分镜完全按它施工：

```bash
# 骨架：ffprobe 量实际时长 + 按行均分
mvwb timeline \
  <项目>/01-歌词/歌词.md <项目>/02-音乐/歌曲_v2.mp3 --out <项目>/02-音乐/时间轴.md
```

骨架是均匀分配的，然后**逐句校准**：请用户听定位每句进点（或用 ffmpeg 按 start 切 2–3 段给用户确认）。格式（镜头列默认一行一镜）：

```markdown
| # | 歌词 | 开始 | 结束 | 镜头 |
|---|---|---|---|---|
| 1 | 地铁呼啸穿过耳边的风 | 3.0 | 7.2 | 镜1 |
```

校准完 status=`locked`（`timeline` 字段登记）。提醒：时间轴改一句 = 分镜改一镜，进第 3 步后尽量少动。
