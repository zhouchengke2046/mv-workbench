# MV 批量工作台 · 数据契约 v0.3

## 数据流

```
原文（只读，内容不改）
├─ 原文/lyric_original.md        甲方歌词：歌名 + 主歌/副歌
└─ 原文/story_script.md          甲方故事脚本：人物 + 场次 + 叙述（不拆镜）
        │
        ▼
每条 MV
├─ 02_storyboard/storyboard_v1.json   标准分镜（景别/运镜/画面描述/时长）
├─ 01_music/timeline_v{n}.json        音乐时间轴
├─ 01_music/song_v{n}.mp3
├─ 03_assets/assets_v{n}.json         关键资产图
├─ 04_clips/clip_manifest_v{n}.json   视频段（prompt+shot_ids+intended）
└─ 04_clips/trim_manifest_v{n}.json   粗剪
        │
        ▼
workbench.html（静态只读模板）
三大项：音乐 / 资产图 / 分镜表
```

## 三大项

| 项 | 展示 | 关键字段 |
|---|---|---|
| 音乐 | 生成几次列几条 + 音频 | 模型、费用、时间、当前/历史；时长在音频里；状态只环颜色 |
| 资产图 | 关键角色/场景/产品 | 名字在上、分辨率右下、模型/费用/时间在下 |
| 分镜表 | 前两列：视频 / 视频段 | 视频分辨率右下、模型/费用/时间/时长在下；镜号/对应句/景别/运镜/画面描述/时长 |

- **视频段**：按分镜关联切分的生成单位，1 段可含 1+ 镜，**≤10s**。
- **视频**：该段生成视频的站位；每段可多条，历史折叠在视频列；每条带分辨率、模型、费用、时间、时长。
- 分镜表每 MV 一份；原文故事脚本不拆镜。

## 文件职责

| 文件 | 谁写 | 谁读 | 关键内容 |
|---|---|---|---|
| `原文/lyric_original.md` | 甲方 | 模板 | 歌词原文，不改 |
| `原文/story_script.md` | 甲方 | 模板 | 故事脚本原文，不拆镜 |
| `02_storyboard/storyboard_v1.json` | 分镜生成 | 模板/视频 | shot_size/camera/visual/duration |
| `01_music/timeline_v{n}.json` | 音乐阶段 | 分镜/粗剪 | line_id/start/end/confidence |
| `03_assets/assets_v{n}.json` | 资产阶段 | 模板 | 关键图 + 元数据 |
| `04_clips/clip_manifest_v{n}.json` | 视频阶段 | 粗剪/模板 | 视频段 prompt/shot_ids/intended |
| `04_clips/trim_manifest_v{n}.json` | 粗剪 | 剪辑 | source_in/out/confidence/flags |

## 状态

每条 MV 三段：`music / assets / video`（分镜表属于视频段的展示层）。
模板只显示 MV 三段环颜色，不显示状态文字；状态字段仍在 JSON/DATA。

- 音乐 `locked` 后不可重跑/解锁；换音乐=新建 MV。
- 改资产 → 视频/分镜表 `stale`；分镜新版本 → 视频 `stale`。
- 每次生成/重跑写新版本 + `runs` 历史；HTML 只读。

## 硬约束

1. **原文不改**：歌词/故事脚本只展示；不改写、不拆镜。
2. **分镜四要素**：景别、运镜、画面描述、时长。
3. **分镜表前两列**：视频、视频段。
4. **视频段≤10s**，可含 1+ 镜。
5. **每段可多条视频**：历史折叠；视频分辨率在右下角，下方模型/费用/时间/时长。
6. **资产只列关键图**：名字在上、分辨率右下、模型/费用/时间在下。
7. **音乐生成几次列几条**：模型/费用/时间/当前或历史；时长在音频里；状态只环颜色。
8. **HTML 只读**：静态版无按钮/表单/接口；服务版只多 Key 配置按钮/弹窗（`mv_keys_server.py`），原始 key 不进 HTML；重跑由 agent 改 JSON + 更新 DATA。

## 示例

- `demo/`：3 条演示 MV（ready/draft/not_started）+ `workbench.html`；
- `golden-sample/`：粗剪黄金样本。

## 校验

```bash
python3 - <<'PY'
import json, glob
for f in glob.glob("contracts/*.schema.json"):
    json.load(open(f)); print("ok", f)
PY
```
