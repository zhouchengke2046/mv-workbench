---
name: zz-mv-gongzuotai
description: MV 项目统筹 skill：从甲方歌词/故事脚本生成静态 workbench.html，按 MV 生成音乐计划、资产清单、标准分镜和视频段计划，再逐项生成音乐、资产图、视频段并审核重跑。最终产物是每个 MV 一个本地目录（音乐/资产/视频段 + handoff），不含粗剪和成片。Key/余额/服务用 mvwb；模型提示词和 RunningHub/Router 用法在本 skill 的 references/ 内。
---

# zz-mv-gongzuotai · 单 skill 的 MV 项目统筹

## 定位

- 这是整个 MV 项目的**唯一入口 skill**。
- 工作台只展示与统筹；生成由 agent 调用本 skill 的 `scripts/` 完成。
- 流程到**视频段**结束：不粗剪、不拼片、不做成片；视频段 + handoff 交给下一阶段剪辑。

> 命令里的 `mvwb` 指安装后的全局命令；如果 `~/.local/bin` 不在 PATH，用 `~/.agents/skills/zz-mv-gongzuotai/mvwb`（或 `zz-mv-gongzuotai/scripts/mvwb.py`）。

## 打开方式（硬规则）

- **配置 Key / 看余额 / 用户说“打开工作台”**：必须用服务版 `mvwb open`，打开 `http://127.0.0.1:8776/go`。
- **禁止**用 `file://`、`python -m http.server`、旧端口/旧服务来配置 Key。
- 静态 `file://` 只用于**只读分享**；没有配置按钮是设计，不是 bug。
- 页面没有按钮时：先看地址栏和 `document.documentElement.dataset.mvMode`：
  - `static` → 运行 `mvwb open`，不要调试页面；
  - `service` 且 `typeof openKeyConfig !== "function"` → 才是 UI 注入 bug。
- `mvwb status` 可查服务是否在跑；`mvwb open` 会自动复用/启动服务并选空闲端口。

## 最终交付

每个 MV 一个目录，音乐、资产、视频段都在里面：

```text
workspaces/<project>/
├─ 原文/
│  ├─ lyric_original.md      甲方歌词原文
│  ├─ story_script.md        甲方故事脚本原文（不拆镜）
│  └─ lyric.json             L01… 行号映射
├─ workbench.html            项目工作台（只读展示）
└─ MV001/
   ├─ mv_manifest.json       阶段状态/版本/成本
   ├─ 00_framework.md        音乐/资产/分段计划
   ├─ 01_music/
   │  ├─ song_v1.mp3
   │  └─ timeline_v1.json    每句起止秒（供分段/交付）
   ├─ 02_assets/
   │  ├─ assets_v1.json
   │  ├─ role_xxx.png
   │  ├─ scene_xxx.png
   │  └─ prop_xxx.png
   ├─ 03_segments/
   │  ├─ segments_v1.json    G1/G2… 当前版本 + 历史
   │  ├─ G1_v1.mp4
   │  ├─ G1_v2.mp4           审核重跑的历史
   │  └─ G2_v1.mp4 …
   └─ handoff_v1.json        交给剪辑的清单
```

`handoff_v1.json` 只包含剪辑需要的字段：

```json
{
  "mv_id": "MV001",
  "status": "ready",
  "segments": [
    {
      "segment_id": "G1",
      "line_ids": ["L01", "L02"],
      "music_start": 0.0,
      "music_end": 6.0,
      "duration": 6.0,
      "video_file": "03_segments/G1_v1.mp4",
      "model": "muse-video-ext",
      "resolution": "720x1280",
      "notes": "审核通过的当前版本"
    }
  ]
}
```

## 四步

### Step 1 · 原文

1. 先找 `原文/`、`甲方资料/`、`输入/` 下的歌词/脚本；文件名含 `歌词`、`lyric`、`脚本`、`script`。
2. 找到就只读入库，不改写、不拆行、不“优化”。
3. 没找到：先问用户有没有甲方资料；没有就按产品/故事/人物/风格/时长/参考引导，生成草稿。
4. 入库：

```text
原文/lyric_original.md   歌名/主歌/副歌，原文
原文/story_script.md     故事脚本原文，不拆镜
原文/lyric.json          L01… 行号映射
```

**门：原文确认。** 用户说“没问题/用这版”后锁定；改原文=重新起工作台。

### Step 2 · 空工作台

```bash
mvwb init my_project
# 替换 workspaces/my_project/原文/ 后，让 agent 生成空工作台
```

Agent 用 `templates/workbench.html` + `DATA.json` 构建：

```bash
python3 scripts/build_workbench.py \
  --template templates/workbench.html \
  --data workspaces/my_project/data.json \
  --out workspaces/my_project/workbench.html
```

打开服务版：

```bash
mvwb open --workspace my_project
```

生成后停下来问：

1. **一次生成多少条？**（建议先 5–10 条打样）
2. **每条多长？**（15/30/45/60s）
3. **什么风格？**（3D 皮克斯 / 真人短剧 / 日系治愈 / 甲方参考片）

**门：批次参数确认。** 此步不花钱。

## 时长契约（用户目标 vs 音乐实际）

| 时长 | 谁定 | 用途 |
|---|---|---|
| `target_duration` | 用户在第 2 步设定（如 45s） | 音乐请求秒数、MV 总目标时长、预算/段数、框架计划 |
| `actual_duration` / `timeline_v1.json` | 音乐生成后读取 | 分镜/视频段实际时长、Muse `seconds`、H3 帧数、handoff |

- **总时长按用户设定**：音乐生成时把 `target_duration` 传给 ACE 的 `116:value`；框架的总时长、段数、预算都按它规划。
- **每段时长按音乐实际**：音乐出来后读 `actual_duration` 和逐句 `timeline`，更新分镜/视频段的 `duration`；视频段按实际句长生成，不按计划时长硬切。
- **偏差处理**：实际与目标差 >1s 或 >2% 时暂停，让用户选「接受实际 / 重生成音乐 / 后期裁」；不要偷偷用计划时长生成视频。
- **只选视频没音乐**：先用 `target_duration` 做 provisional 计划；补音乐后所有视频段标记 `stale`，按实际时间轴重跑。
- 这样既尊重用户设定的总时长，又保证画面与音乐逐句对齐。

### Step 3 · MV 文本框架

创建 `MV001…MV00N`，每条：

- `mv_manifest.json`：stages 全 `not_started`；genome、cost/spent=0。
- `00_framework.md`：音乐计划、资产清单、标准分镜、视频段计划；这里的 `duration` 是**计划值**，以 `target_duration` 为总目标。
- `03_segments/segments_v1.json`：先写计划，`videos: []`。
- 更新 `DATA.mvs`：音乐/资产为空，分镜/段有计划；保留 `keys` 快照。

给用户看框架摘要：

> 框架有没有要改的？要改哪条 MV、哪个镜头、哪句？只改你点名的部分。

**门：框架审核通过 + 生成范围/报价确认。**

### Step 4 · 生成与审核

#### 4.0 预检

```bash
mvwb keys status
mvwb keys balance
mvwb quote --model muse-video-ext --seconds 2
```

缺 Key / 余额不足 / 查询失败：停。报价 = 数量 × 单价；用户确认才跑。

#### 4.1 顺序：音乐 → 时间轴 → 资产 → 视频段

| 步骤 | 命令 | 产物 |
|---|---|---|
| 音乐 | `mvwb rh --app 2075301815628943362 ...` | `01_music/song_v1.mp3` |
| 时间轴 | `mvwb timeline ...` | `01_music/timeline_v1.json` |
| 资产 | `mvwb rh --app 2116462203997081601 ...` | `02_assets/*` + `assets_v1.json` |
| H3 视频 | `mvwb rh --wf 2110943749894402050 ...` | `03_segments/G*_v1.mp4` |
| Muse 视频 | `mvwb muse --prompt ... --seconds N --size 720x1280 --out ...` | `03_segments/G*_v1.mp4` |
| 交付 | 写 `handoff_v1.json` | 给剪辑 |

- **音乐先锁定**；读实际 `duration/timeline` 后更新段时长；资产按参考包；视频段按实际句长逐段生成。
- 每段可生成多条视频：当前第一条，历史追加 `G1_v2.mp4`。
- 新版本写 `*_v{n+1}.json`，不覆盖旧版。
- 更新 `stages/status/spent`，重建 `DATA`。

#### 4.2 审核循环

> 生成完了，哪些要改？要改哪条 MV、哪个视频段、哪张图/哪首歌？

- 只重跑点名项；新版本 + 历史。
- 音乐 `locked` 后不可改；换音乐 = 新建 MV。
- 资产改动 → 依赖它的视频段标记 `stale`。
- 分镜/视频段计划改动 → 对应视频段 `stale`。
- 用户说“定稿/通过” → 对应 stage `locked`。

#### 4.3 交付

所有视频段 `locked` 后：

- 写 `handoff_v1.json`（或 `handoff_v1.csv`）。
- 检查每个段：`video_file` 存在、`duration` ≤10s、`music_start/end` 与时间轴一致。
- 项目结束；剪辑拿视频段和 handoff 进入下一阶段。

## 审核/版本规则

| 状态 | 含义 | UI |
|---|---|---|
| `not_started` | 未生成 | 灰环 |
| `draft` | 有产物待审 | 琥珀环 |
| `locked` | 已定稿 | 绿环 |
| `stale` | 上游改了，需重跑 | 橙环 |
| `failed` | 失败 | 红环 |

- 上游未 `locked`，下游不开始。
- 只改点名处；其他逐字保留。
- 历史不覆盖；`spent` 累计历史成本。
- 工作台只显示环颜色，不显示状态文字。

## 模型与提示词路由

| 阶段 | 默认 | 看哪个 reference |
|---|---|---|
| 音乐 ACE-Step | `2075301815628943362` | `references/prompts/ace.md` |
| 资产 MOSS | `2116462203997081601` | `references/prompts/moss.md` |
| H3 多参视频 | `2110943749894402050` | `references/prompts/h3.md` |
| Muse 视频（Router） | `muse-video-ext` | `references/prompts/muse.md` |
| S2V 口型 | `1979183169033375745` | `references/prompts/h3.md` |
| RunningHub API | — | `references/providers/runninghub.md` |
| Router API/余额 | — | `references/providers/router.md` |
| 工作台 DATA 契约 | — | `references/workbench-contract.md` |
| 交付字段 | — | `references/handoff.md` |

- 视频按段确认模型；不同段可不同模型，但同一 MV 风格包/调色统一。
- 多参考图：角色四视图/场景板/道具/产品实拍；一图一职；先跑 1 段样板。

## Key

- 唯一真源：`~/.config/mv-workbench/keys.json`（0600）。
- 页面配置：`mvwb open` → 右上角“配置 Key” → RunningHub / Router 两个输入框。
- 命令行：`mvwb keys set runninghub`、`mvwb keys set router`。
- 原始 Key 不进 HTML/DATA/日志；`DATA.keys` 只有掩码和余额。
- 生成命令统一经 `mv_keys.py exec` 注入；不要依赖 shell 残留 Key。

## 常用命令

```bash
mvwb doctor
mvwb open
mvwb open --workspace my_project
mvwb init my_project
mvwb keys status
mvwb keys balance
mvwb quote --model muse-video-ext --seconds 2
mvwb build --data workspaces/my_project/data.json --out workspaces/my_project/workbench.html
mvwb rh --app <id> --name <tag> --overrides <json> --out <dir>
mvwb muse --prompt "..." --seconds 2 --size 720x1280 --out out.mp4
mvwb timeline <lyric.json> <audio.mp3> --out <dir>
```

## 不做什么

- 不粗剪、不拼片、不做字幕/混音/成片。
- 不自动审核；用户提出修改后只重跑点名项。
- 不把客户歌词/脚本/素材提交到公开仓库。

## 文件

```text
SKILL.md
scripts/          mvwb、keys/server、build、timeline、providers
references/       workbench 契约、提示词、provider、handoff
templates/        workbench.html
contracts/        timeline/storyboard/segments/mv 契约
demo/             原创 demo
config/           模型价格 / provider / keys 示例
```

## 版本

- v0.2.7（2026-11-13）：skill 正式命名为 `zz-mv-gongzuotai`；安装目录/压缩包同步改名。
- v0.2.6（2026-11-13）：Windows 测试解码修复（CLI 输出 UTF-8）。
- v0.2.5（2026-11-13）：Windows `mvwb status` 端口探测超时修复。
- v0.2.4（2026-11-13）：新增 `mvwb open/status`；静态页提示“Key 需服务版”；打开方式硬规则。
- v0.2.3（2026-11-13）：清理冗余资产、合并 Muse 指南、补 target/actual 时长契约。
- v0.2（2026-11-13）：单 skill 重构；factory/trim 移除；流程到视频段；每 MV 独立目录；handoff。
- v0.1：公开打包初版。
