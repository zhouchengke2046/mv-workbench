# 四步执行契约（输入 → 输出 → 自检 → 门）

> `zz-mv-gongzuotai` 的内部执行规范。每一步都按同一结构执行；缺输入、缺产物、自检失败，都不进入下一步。

## 总则

1. **先问后做**：只问缺失项，每项给默认值；用户没回答的按默认值继续，并在输出里注明“按默认”。
2. **一步一产物**：每步结束必须落盘，不能只在对话里描述。
3. **输出统一**：对话只给「结论 1 行 + 产物相对路径 + 自检结果 + 下一步/待确认」。不贴整段 JSON，不复述模板。
4. **自检必须真跑**：引用命令输出，不允许“应该可以/已确认”。失败就停，不静默跳过。
5. **提醒格式统一**：失败/阻塞/警告一律用 `scripts/alerts.py` 的代码表（见 `references/alerts.md`）；学生整块转发给老师，禁止裸报错、禁止直接“找老师要 Key”。
6. **状态词固定**：`not_started | planning | generating | draft | review | locked | stale | failed`。
7. **版本不覆盖**：新版本 `v2/v3`，旧版保留；音乐锁定后不换歌。
8. **成本分账**：`cost` 是计划，`spent` 是实际；Router 一律「CNY」且按**账单实扣**写数（生成后用 `keys balance` 的 usage delta 回填），报价（quote/fx）只作预算参考；不混算。

## 统一输出模板

```text
Step X · 名称：完成/未完成
产物：
- <相对路径>
自检：
- <命令> → <关键结果>
需要你确认：
- <最多 3 项；没有就写“无，进入下一步”>
```

---

## Step 0 · 项目初始化

**输入**

| 项 | 必填 | 默认 |
|---|---|---|
| 项目名 | 是 | 客户名/日期 |
| 歌词或参考脚本 | 是 | — |
| MV 数量 | 否 | 1 条打样 |
| 每首时长 | 否 | 30s |
| 风格 | 否 | 按参考包 |
| 比例 | 否 | 9:16 竖屏（1080×1920） |
| 人物/场景/产品参考 | 否 | 文字描述 |
| 预算上限 | 否 | 先报价再定 |

**动作**

```bash
mvwb init <project>          # 空项目：原文/ 待填、mvs=[]、已生成 workbench.html
mvwb init <project> --demo   # 需要示例时：复制完整 demo
```

**产物**

```text
workspaces/<project>/
├─ 原文/                 （待填）
├─ data.json
└─ workbench.html
```

**自检**

```bash
mvwb check --data workspaces/<project>/data.json
mvwb open --workspace <project> --no-open
```

- `check` 缺失/空文件必须为 0。
- 打印的 `workbench.html` 路径必须存在。

**门**：用户确认项目名、MV 数量、时长、比例、预算。

---

## Step 1 · 原文

**输入**：甲方歌词/参考脚本（文本、表格、文档均可）。

**动作**

- 原样保存，不改写、不拆镜。
- 生成行号映射：每句一个 `L01…`，空行不编号。

**产物**

```text
原文/
├─ lyric_original.md     标题/主歌/副歌，保留甲方原文
├─ story_script.md       甲方参考脚本原文（不拆镜，供改编）
└─ lyric.json            [{id, text, section}]
```

**自检**

- `lyric.json` 行数 = 原文有效行数。
- 每行 id 连续、无重复、无空文本。
- 脚本没有被拆成“镜头 1/2/3”。

**门**：用户核对原文与行号；有错别字先改，再进入 Step 2。

---

## Step 2 · 空工作台

**输入**：Step 1 + Step 0 参数。

**产物**

- `data.json`：`meta / keys / lyric / script / mvs[]`；`mvs` 先建空的 `MV001…`，stages=`not_started`。
- `workbench.html`：由模板 + DATA 构建，纯静态。

**自检**

```bash
mvwb build --data workspaces/<project>/data.json --out workspaces/<project>/workbench.html
mvwb check --data workspaces/<project>/data.json
```

- `check` 缺失/空文件 = 0。
- **Key 导入后必须刷新快照**：`mvwb keys import …` → `mvwb keys balance --data <项目>/data.json` → `mvwb build`。漏跑 balance 会导致工作台顶部显示「未配置」、spent 不更新（E2E 实测踩坑）。
- HTML 中不出现原始 Key（构建器会拒绝）。
- 双击 HTML 能打开；左侧有原文与 MV 列表；每 MV 有音乐/资产/脚本/分镜四块占位。

**门**：用户确认工作台能看、参数正确。

---

## Step 3 · MV 文本框架

**输入**：Step 2 工作台 + 审核意见。

**产物（每个 MV）**

```text
MV001/
├─ mv_manifest.json          stages/status/version/cost/spent
├─ 00_script.md              画面脚本：据参考脚本改编的本 MV 画面故事
├─ 00_framework.md           音乐计划/资产清单/分镜/段计划
└─ 03_segments/segments_v1.json   shots + segments，videos=[]
```

**硬规则**

- **改编逻辑（骨架保留 · 歌词不动 · 画面对词）**：参考脚本是甲方原文，原样保留、不改写，只提供骨架（人物/场景/情节走向/风格）。每条 MV 先据骨架改编出自己的画面脚本（`00_script.md`），再从画面脚本拆分镜；分镜表与画面脚本必须一致。**歌词固定不变**——画面脚本和分镜不得改写、增删任何一句歌词；**画面必须匹配歌词**——每个镜头的 `visual` 要能对应它覆盖的歌词句，画面讲的事和歌词说的事不能对不上（对不上时先改画面脚本，再重拆分镜）。
- 总时长按 `target_duration`；每段 ≤10s，至少 1 个镜头。
- 每句歌词必须落在某个 segment 的 `line_ids` 里，不能漏句。
- 资产清单至少包含：角色、主场景、关键道具（按项目需要）。
- 比例默认 9:16；资产按用途给分辨率。
- 每条先写 `genome`：`cast_id/outfit_id/face_seed`、`story_id`、`music`、`visual`、`edit`；规则见 `references/variation.md`。
- 输出差异化表；同批任意两条至少 3 个维度不同，禁止相同 `cast+outfit`、相同故事矛盾、相同 `genre+BPM+vocal`、相同场景包。

**自检**

- 每条 MV 都有 `00_script.md` 画面脚本；每个镜头能在画面脚本里找到对应情节。
- **画面对词**：逐镜核对 `visual` 与其 `line_ids` 的歌词内容能对应；歌词与甲方原文逐字一致（未被改写/增删）。
- 段时长之和与目标时长差 ≤1s。
- 每段 `line_ids` 连续且覆盖全部行。
- 每个镜头有景别/运镜/画面描述。
- 差异化表无重复组合；有重复就换池子里的下一个。
- 此时 `videos=[]`，没有生成文件。

**门**：用户逐条审核画面脚本与框架；agent 给出数量 × 单价报价，用户确认后才进入 Step 4。

---

## Step 4 · 生成与审核

### 4.1 音乐

**输入**：框架里的音乐计划（风格/BPM/时长）。

**生成（Router 主链，详见 `references/router-playbook.md`）**

```bash
python3 scripts/providers/tokentech_task.py music \
  --lyrics "<原文结构化歌词，不改写>" --style "<风格包>" \
  --seconds <目标时长> --bpm <BPM> --language zh \
  --out MV001/01_music/song_v1.mp3
```

**产物**：`01_music/song_v1.mp3` + `timeline_v1.json`。

**自检**

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 MV001/01_music/song_v1.mp3
mvwb timeline 原文/lyric.json MV001/01_music/song_v1.mp3 --out MV001/01_music/timeline_v1.json
```

- 时间轴 json 行数与 `lyric.json` 一致；音乐快照（ID3 TXXX）里风格/歌词/时长应为本次任务值。

- 实际时长与目标差 >1s 或 >2%：暂停，让用户选接受/重生成/后期裁。
- 时间轴行数与 `lyric.json` 一致。
- 用户确认后 music `locked`。

### 4.2 资产

**输入**：资产清单 + 参考图。

**生成（Router 主链）**

```bash
python3 scripts/providers/tokentech_task.py image \
  --prompt "<清单项完整提示词（三视图用 casting-style.md §3 模板）>" \
  --negative "blurry, deformed hands, watermark, garbled text" \
  --seed <固定> --out MV001/02_assets/<name>_v1.png
```

**产物**：`02_assets/*.png` + `assets_v1.json`。

**自检**

- 分辨率符合清单；无文字/水印/多余肢体。
- 角色三视图按 `references/prompts/moss.md`：左格正面头肩、中格正面全身但**头部完全不入画**、右格背面；纯色无缝背景；不要四视图。
- 角色卡/风格包见 `references/prompts/casting-style.md`；每个角色先出 4 张候选，选 1 张再锁定。
- 场景：空镜、无人物、大全景 45° 俯视；道具：纯底、无手。
- 每张给 `qa: pass | warn | fail`；`fail` 必须重跑，`warn` 要用户确认后才能用。
- 资产 `locked` 后，改资产要把依赖视频段标 `stale`。

### 4.3 视频段

**输入**：已锁定音乐 + 时间轴 + 资产 + 段计划。

**生成（Router 主链 · R2V 是默认：人物镜头必须带参考图，禁止纯文生）**

**提示词按模型自动匹配方言（只读命中的一份，不要互相套用）**：

| 模型 | 提示词方言 | 写法文件 |
|---|---|---|
| `muse-video-ext` | 时间线式短文（人物锚定+场景锚定+逐秒时间线+风格收束） | `references/prompts/muse.md` |
| `minimax-h3-rh-ck` | 八段长文（43.text，官方结构）+ nodeInfoList 参数 | `references/prompts/h3.md` |

模型选 `muse-video-ext`（默认，便宜快速）：

```bash
python3 scripts/providers/tokentech_video.py \
  --prompt "<muse 方言：按画面脚本的多镜头时间线提示词>" \
  --seconds <段时长> --size 720x1280 --resolution 720p \
  --image-urls "<角色三视图URL>" "<主场景URL>" --image-field image_urls \
  --out MV001/03_segments/G1_v1.mp4
```

模型选 `minimax-h3-rh-ck`（一致性要求更高时）：

```bash
# 八段长文走 /v1/responses 任务协议，配方见 references/prompts/h3.md
```

图源用中转站产物签名 URL（`*_meta/meta.json` 的 `artifact_url`）；空镜/氛围镜头可只带场景图或不带图。
资产提示词一律走 `references/prompts/moss.md` 固定范式（九段式双语）+ 机检
`python3 scripts/check_asset_prompts.py 图片提示词.md`。

**产物**：`03_segments/G1_v1.mp4`，历史 `G1_v2.mp4`。

**自检**

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 MV001/03_segments/G1_v1.mp4
```

- 抽帧比对角色与三视图（发型/服装/体型）：明显不符 → 提示词补角色细节或换 seed 重跑 v2。

- 每段 ≤10s；实际时长与 segment `duration` 差 ≤0.5s。
- 画面比例 9:16；能播放；无黑屏/花屏。
- 新版本写 `v2`，旧版保留；只有用户点名才重跑。
- 用户确认后 video `locked`。

### 4.4 交付

**产物**：`handoff_v1.json`。

**自检**

- 每个 segment 的 `video_file` 存在且非空。
- `music_start/end` 与 `timeline_v1.json` 一致。
- `line_ids` 覆盖全部歌词行。
- `duration` ≤10s。

**门**：所有段 `locked`，用户确认交付；项目结束。

---

## 失败处理

| 情况 | 动作 |
|---|---|
| 缺 Router Key | 停；发 **K001** 提醒（学生导入 `zz-keys.json` 或在工作台填写） |
| 余额不足/查询失败 | 停；给出余额快照与充值建议 |
| Router 连续失败 | 同平台重试 1 次；10 分钟内 ≥3 次且未配备用 → 发 **B001** 提醒，学生转发给老师；老师发放备用 `zz-keys.json` 后导入即启用 |
| 生成失败 | 发 **P3/P4** 提醒（保留错误原文 ≤300 字）；不重复提交 |
| 自检失败 | 发 **W1–W3** 提醒；修当前项，修不了就停 |
| QA `fail` | 发 **Q1** 提醒；自动重跑 1 次，仍失败让用户决定 |
| 用户提出修改 | 只重跑点名项，新版本，旧版保留 |
| 改风格/比例/时长（大改） | 先给影响范围 + 重跑报价（¥）；用户确认后再动 |
| 音乐时长偏差 >1s/2% | 发 **T1** 提醒；用户选接受/重做/后期裁 |

## 自检命令速查

```bash
mvwb doctor
mvwb keys status
mvwb keys balance --data workspaces/<project>/data.json
mvwb build --data workspaces/<project>/data.json --out workspaces/<project>/workbench.html
mvwb check --data workspaces/<project>/data.json
mvwb quote --model muse-video-ext --seconds 6
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 <file>
```
