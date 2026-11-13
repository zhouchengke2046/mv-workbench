# MV 工作台 · 数据契约 v0.4

## 数据流

```text
原文（只读，不改）
├─ 原文/lyric_original.md        甲方歌词：歌名 + 主歌/副歌
└─ 原文/story_script.md          甲方故事脚本：人物 + 场次 + 叙述（不拆镜）
        │
        ▼
每条 MV
├─ 01_music/timeline_v{n}.json   音乐逐句时间轴
├─ 01_music/song_v{n}.mp3
├─ 02_assets/assets_v{n}.json    关键资产图
├─ 03_segments/segments_v{n}.json 视频段（prompt + shot_ids + 当前/历史视频）
└─ handoff_v1.json               交给剪辑的清单
        │
        ▼
workbench.html（静态只读）
三大项：音乐 / 资产图 / 分镜表
```

## 三大项

| 项 | 展示 | 关键字段 |
|---|---|---|
| 音乐 | 生成几次列几条 + 音频 | 模型、费用、时间、当前/历史；时长在音频里；状态只环颜色 |
| 资产图 | 关键角色/场景/产品 | 名字在上、分辨率右下、模型/费用/时间在下 |
| 分镜表 | 前两列：视频 / 视频段 | 视频分辨率右下、模型/费用/时间/时长在下；镜号/对应句/景别/运镜/画面描述/时长 |

- **视频段**：生成单位，1 段可含 1+ 镜，**≤10s**。
- **视频**：该段当前版本 + 历史；每条带分辨率、模型、费用、时间、时长。
- 每条 MV 自己的音乐/资产/视频段都在 `MVxxx/` 下。

## 文件职责

| 文件 | 谁写 | 谁读 | 关键内容 |
|---|---|---|---|
| `原文/lyric_original.md` | 甲方 | 模板 | 歌词原文，不改 |
| `原文/story_script.md` | 甲方 | 模板 | 故事脚本原文，不拆镜 |
| `01_music/timeline_v{n}.json` | 音乐阶段 | 分镜/分段/交付 | line_id/start/end |
| `02_assets/assets_v{n}.json` | 资产阶段 | 模板 | 关键图 + 元数据 |
| `03_segments/segments_v{n}.json` | 视频阶段 | 模板/交付 | 段 prompt/shot_ids/videos |
| `handoff_v1.json` | 交付 | 剪辑 | 段 → 视频文件 + 音乐起止 |

## 状态

每条 MV 三段：`music / assets / video`。
模板只显示 MV 三段环颜色，不显示状态文字；状态字段仍在 JSON/DATA。

- 音乐 `locked` 后不可重跑/解锁；换音乐=新建 MV。
- 改资产 → 依赖它的视频段 `stale`；改分镜/段计划 → 对应视频段 `stale`。
- 每次生成/重跑写新版本；旧版保留；HTML 只读。

## 硬约束

1. **原文不改**：歌词/故事脚本只展示；不改写、不拆镜。
2. **分镜四要素**：景别、运镜、画面描述、时长。
3. **分镜表前两列**：视频、视频段。
4. **视频段≤10s**，可含 1+ 镜。
5. **每段可多条视频**：当前第一条，历史追加；分辨率右下。
6. **资产只列关键图**：名字在上、分辨率右下、模型/费用/时间在下。
7. **音乐生成几次列几条**：模型/费用/时间；时长在音频里；状态只环颜色。
8. **HTML 只读**：纯静态，无按钮/接口/服务；Key/余额由 agent 写入 `DATA.keys` 快照；原始 key 不进 HTML。
9. **不做粗剪/成片**：项目到视频段 + handoff 结束。

## 示例

- `demo/`：3 条演示 MV（ready/draft/not_started）+ `workbench.html`；
- 每个 MV 的 `01_music/02_assets/03_segments` 是产物目录样板。

## 校验

```bash
python3 - <<'PY'
import json, glob
for f in glob.glob("contracts/*.schema.json"):
    json.load(open(f)); print("ok", f)
PY
```
