---
name: zz-mv-gongzuotai
description: MV 项目统筹 skill：从甲方歌词/故事脚本生成静态 workbench.html，按 MV 生成音乐计划、资产清单、标准分镜和视频段计划，再逐项生成音乐、资产图、视频段并审核重跑。最终产物是每个 MV 一个本地目录（音乐/资产/视频段 + handoff），不含粗剪和成片。Key/余额用 mvwb；模型提示词和 RunningHub/Router 用法在本 skill 的 references/ 内。
---

# zz-mv-gongzuotai · 单 skill 的 MV 项目统筹

## 定位

- 这是整个 MV 项目的**唯一入口 skill**。
- 工作台只展示与统筹；生成由 agent 调用本 skill 的 `scripts/` 完成。
- 流程到**视频段**结束：不粗剪、不拼片、不做成片；视频段 + handoff 交给下一阶段剪辑。

> 命令里的 `mvwb` 指安装后的全局命令；如果 `~/.local/bin` 不在 PATH，用 `~/.agents/skills/zz-mv-gongzuotai/mvwb`（安装时已复制并加执行位）；如果仍不可用，用 `python3 ~/.agents/skills/zz-mv-gongzuotai/scripts/mvwb.py`。

## 工作台与 Key（硬规则）

- **工作台是项目里的静态 `workbench.html`**：直接双击/用浏览器打开 `file://...`；**不启动任何后台服务**。
- **禁止** `mvwb server`、`python -m http.server`、端口、服务版、旧 Key 页面。工作台右上角“配置 Key”只下载导入文件，不联网、不写页面；没有服务。
- 用户说“打开工作台”：运行 `mvwb open [--workspace NAME]`，它只打开本地 HTML。
- **老师统一发放 Key**：学生把 `zz-keys.json` 放到项目根目录；agent 运行 `mvwb keys import --file <项目>/zz-keys.json --delete-source`。导入一次即全局生效，发放文件导入后删除。文件只需两个字段：`{"runninghub": "...", "router": "..."}`；可选元数据见 `references/key-distribution.md`。
- **Key 由用户在本地工作台填写**：打开 `workbench.html` → 右上角“配置 Key” → 填两个 Key → 下载 `mv-keys-import.json`；用户对 agent 说“导入下载目录的 mv-keys-import.json”，agent 运行 `mvwb keys import --file <path> --delete-source`。也可双击 `setup-keys.command` / `setup-keys.cmd`，或终端 `mvwb keys set`。agent 只引导，不索要 Key；非交互环境不要调用 `keys set`。
- **免二次对话**：agent 可先运行 `mvwb keys watch --timeout 600 [--data <data.json>]`；用户在工作台填完并下载后，watcher 自动导入、删除下载文件；带 `--data` 时顺便刷新余额并重建工作台。
- Key 不写进 DATA、HTML、脚本、日志或截图；下载的导入文件导入后必须删除。用户已经把 Key 发到对话里时，提醒他作废重发。
- **余额由 agent 刷新**：`mvwb keys balance --data <data.json>` → `mvwb build`；页面只显示掩码和快照时间，不联网。
- **每次生成/替换文件后**：更新 `data.json` → `mvwb build` → `mvwb check --data ...`。`check` 报缺失就是工作台不会显示，不能算完成。

## 最终交付

每个 MV 一个目录，音乐、资产、视频段都在里面：

```text
workspaces/<project>/
├─ 原文/
│  ├─ lyric_original.md      甲方歌词原文
│  ├─ story_script.md        甲方故事脚本原文（不拆镜）
│  └─ lyric.json             L01… 行号映射
├─ workbench.html            项目工作台（只读展示 + 本地 Key 导入）
├─ data.json                 工作台数据源（agent 更新）
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

## 执行契约（每步必做）

详细输入/输出/自检见 `references/step-contract.md`。每一步固定五件事：

| 步骤 | 先问（缺失才问） | 产物 | 自检 | 门 |
|---|---|---|---|---|
| 0 初始化 | 项目名、数量、时长、风格、比例、预算 | workspace + `data.json` + `workbench.html` | `mvwb check` = 0 缺失 | 参数确认 |
| 1 原文 | 歌词/脚本文件 | `原文/*` + `lyric.json` | 行数/id 连续/未拆镜 | 原文核对 |
| 2 空工作台 | 批次参数 | DATA + 静态 HTML | build + check + 双击可开 | 工作台确认 |
| 3 框架 | 审核意见 | manifest + framework + segments | 时长/漏句/段≤10s | 框架确认 + 报价 |
| 4 生成 | 点名项 | 音乐/资产/视频段/handoff | 文件存在/时长/QA/时间轴 | 逐项 locked |

- 对话输出统一为「结论 + 产物路径 + 自检结果 + 待确认」，不贴整段 JSON。
- 自检必须真跑并引用结果；失败停在当前步，不静默进入下一步。

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
mvwb init my_project          # 空项目：原文/ 待填、mvs=[]、已生成 workbench.html
mvwb init demo_project --demo # 需要示例时：复制完整 demo
# 填 workspaces/my_project/原文/ 后，让 agent 生成空工作台
```

Agent 用 `templates/workbench.html` + `DATA.json` 重建：

```bash
python3 scripts/build_workbench.py \
  --template templates/workbench.html \
  --data workspaces/my_project/data.json \
  --out workspaces/my_project/workbench.html
```

打开静态工作台：

```bash
mvwb open --workspace my_project
```

生成后停下来问（缺什么问什么，每项给默认值）：

1. **项目名叫什么？** 默认客户名/日期。
2. **一次生成多少条？** 默认 1 条打样（建议先 1–5 条）。
3. **每条多长？** 默认 30s（15/30/45/60s）。
4. **什么风格？** 默认按参考包（3D 皮克斯 / 真人短剧 / 日系治愈 / 甲方参考片）。
5. **比例？** 默认 9:16 竖屏（1080×1920）。
6. **人物/场景/产品参考？** 有图给图，没有用文字描述。
7. **预算上限？** 没给就先报价，不提交。

输出只回：`产物路径 + 自检结果 + 这 7 项确认`。**门：批次参数确认。** 此步不花钱。

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

- **比例默认 9:16 竖屏**（工作台按 1080×1920，Muse 输出 720×1280）；用户明确指定才改。
- **先写 genome**：`cast_id/outfit_id/face_seed`、`story_id`、`music`、`visual`、`edit`；规则见 `references/variation.md`。同批任意两条至少 3 个维度不同，禁止同一角色+同一穿搭、同一故事矛盾、同一 genre+BPM+vocal、同一场景包。
- 输出一张**差异化表**（每条的 cast/story/music/visual/edit）；有重复组合就停，换池子里的下一个，不要开工。

- `mv_manifest.json`：stages 全 `not_started`；genome、cost/spent=0。
- `00_framework.md`：音乐计划、资产清单、标准分镜、视频段计划；这里的 `duration` 是**计划值**，以 `target_duration` 为总目标。
- **资产清单是给用户审核的**：人物三视图/场景空镜/道具，用来锁定后续视频的一致性；不是可选项。向用户解释“没有资产图，每条视频的人物/场景会漂”。
- `03_segments/segments_v1.json`：先写计划，`videos: []`。
- 更新 `DATA.mvs`：音乐/资产为空，分镜/段有计划；保留 `keys` 快照。

给用户看框架摘要：

> 框架有没有要改的？要改哪条 MV、哪个镜头、哪句？只改你点名的部分。

**门：框架审核通过 + 生成范围/报价确认。**

### Step 4 · 生成与审核

#### 4.0 预检

```bash
mvwb keys status
mvwb keys import --file ~/Downloads/mv-keys-import.json --delete-source
mvwb keys watch --timeout 600 --data workspaces/my_project/data.json
mvwb keys balance --data workspaces/my_project/data.json
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
- **资产按角色卡生成**：角色三视图用 `references/prompts/casting-style.md` 的模板 + 风格包；MOSS 规则是左格脸、中格全身但**头部完全不入画**、右格背面。每个角色先出 4 张候选，选 1 张再锁定。
- **同 MV 角色一致**：所有资产/视频段引用同一 `cast_id` 的角色卡和 `outfit_id`；换装只在故事需要时发生并记录。
- **跨 MV 不重复**：同批的 `cast_id`、故事、音乐、场景包按 genome 差异化；资产锁定前抽查两条，避免“同一个人换件衣服就算新 MV”。
- 每段可生成多条视频：当前第一条，历史追加 `G1_v2.mp4`。
- 新版本写 `*_v{n+1}.json`，不覆盖旧版。
- 更新 `stages/status/spent`，重建 `DATA`。
- 重建后必须自检：`mvwb build --data ... --out ... && mvwb check --data ...`；缺失文件数必须为 0，否则先修路径或重新生成。
- 页面是静态 `file://`，相对路径以 `workbench.html` 所在目录为基准；不要手动改成绝对路径。

#### 4.2 审核循环

> 生成完了，哪些要改？要改哪条 MV、哪个视频段、哪张图/哪首歌？

- 只重跑点名项；新版本 + 历史。
- 音乐 `locked` 后不可改；换音乐 = 新建 MV。
- 同批音乐先做近似去重：`genre + BPM 档 + vocal` 不能全同；前 10 秒听起来像同一首就换 `music_id`。
- 资产 `qa: pass / warn / fail`：`fail` 必须重跑；`warn` 要用户确认后才能用。
- 资产改动 → 依赖它的视频段标记 `stale`。
- 分镜/视频段计划改动 → 对应视频段 `stale`。
- 用户说“定稿/通过” → 对应 stage `locked`。

#### 4.3 交付

所有视频段 `locked` 后：

- 写 `handoff_v1.json`（或 `handoff_v1.csv`）。
- 检查每个段：`video_file` 存在、`duration` ≤10s、`music_start/end` 与时间轴一致。
- 项目结束；剪辑拿视频段和 handoff 进入下一阶段。

**下一条 MV**：同一工作台内继续 `MV002`，复用已锁定的音乐/资产规则，先出框架再生成；换歌词/客户用 `mvwb init <项目名>` 新建 workspace，不要覆盖旧项目。

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
| 四步执行契约 | — | `references/step-contract.md` |
| 变体/差异化/去重 | — | `references/variation.md` |
| Key 发放/导入 | — | `references/key-distribution.md` |
| 角色卡/风格/帅哥美女/治愈系 | — | `references/prompts/casting-style.md` |
| 交付字段 | — | `references/handoff.md` |

- 视频按段确认模型；不同段可不同模型，但同一 MV 风格包/调色统一。
- 多参考图：角色三视图（不要四视图）/场景板/道具/产品实拍；一图一职；先跑 1 段样板。

## Key

- 唯一真源：`~/.config/mv-workbench/keys.json`（0600）。
- 配置：`mvwb keys set runninghub`、`mvwb keys set router`（终端隐藏输入）。
- 余额：`mvwb keys balance --data workspaces/<project>/data.json` → `mvwb build`。
- 原始 Key 不进 HTML/DATA/日志；`DATA.keys` 只有掩码和余额快照。
- 生成命令统一经 `mv_keys.py exec` 注入；不要依赖 shell 残留 Key。

## 常用命令

```bash
mvwb doctor
mvwb open
mvwb open --workspace my_project
mvwb init my_project
mvwb keys status
mvwb keys import --file ~/Downloads/mv-keys-import.json --delete-source
mvwb keys watch --timeout 600 --data workspaces/my_project/data.json
mvwb keys balance --data workspaces/my_project/data.json
mvwb quote --model muse-video-ext --seconds 2
mvwb build --data workspaces/my_project/data.json --out workspaces/my_project/workbench.html
mvwb check --data workspaces/my_project/data.json
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
scripts/          mvwb、keys、build、timeline、providers
references/       workbench 契约、step 契约、提示词、provider、handoff
templates/        workbench.html
contracts/        timeline/storyboard/segments/mv 契约
demo/             原创 demo
config/           模型价格 / provider / keys 示例
```

## 版本

- v0.3.9（2026-11-14）：老师发放的 Key 文件统一命名为 `zz-keys.json`；watcher 同时识别 `mv-keys-import*.json` 和 `zz-keys.json`。
- v0.3.8（2026-11-14）：发放 Key 的 JSON 简化为两个字段 `{"runninghub":"...","router":"..."}`；`issued_to`/`expires_at`/`mv_keys_import` 改为可选，只在登记或 watcher 自动拾取时需要。
- v0.3.7（2026-11-14）：新增老师发放 Key 的标准：`zz-keys.json` 放项目根目录，`keys import --delete-source`；格式示例与发放规则见 `references/key-distribution.md`。
- v0.3.6（2026-11-14）：新增 `mvwb keys watch`；agent 先监听下载目录，用户在工作台填 Key 并下载后自动导入/删除，可选刷新余额并重建工作台。
- v0.3.5（2026-11-14）：工作台右上角“配置 Key”本地填 Key → 下载 `mv-keys-import.json` → agent `keys import --delete-source`；无服务、无网络。
- v0.3.4（2026-11-14）：一键 `setup-keys`（Mac/Win）；`keys set` 非交互环境拒绝而不是 traceback；工作台视频缩略图显示首帧；`keys init` 提示改 `--data`。
- v0.3.3（2026-11-13）：新增变体/差异化规则与角色风格提示词包（小红书穿搭/日系甜妹/韩系欧巴/治愈系电影/帅哥美女）；Step 3 要求 genome 与差异化表。
- v0.3.2（2026-11-13）：与用户手册对齐：Key 由用户本机输入；补项目名/三步确认、音乐锁定与时长偏差、资产 QA、大改报价、`data.json` 目录。
- v0.3.1（2026-11-13）：安装升级保留 workspaces；`init` 默认空项目（`--demo` 复制 demo）；build/check 相对路径回退 skill 根目录；精简包内文档。
- v0.3.0（2026-11-13）：移除后台服务，工作台回归纯静态；Key/余额改 CLI；新增四步执行契约与 `mvwb check`；修复透传参数。
