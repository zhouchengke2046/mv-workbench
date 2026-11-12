---
name: zz-mv-gongzuotai
description: MV 工作台四步对话入口：读取甲方歌词/脚本 → 生成静态 workbench.html → 生成 MV 文本框架（音乐/资产/分镜/视频段）→ 按选择生成音乐、资产、视频并审核。Key/余额/服务用 mvwb；模板走 zz-mv-factory；音乐走 ace-music；资产提示词走 zz-manju-image-prompts；视频提示词走 h3-prompt-writing / muse-router；RunningHub 走 zz-runninghub-cli；粗剪走 zz-mv-trim。
---

# MV Workbench · 四步对话（v3.0 public）

## 定位

- 从甲方歌词/参考脚本，生成一个**静态只读**的 `workbench.html`，再按用户选择逐步生成内容。
- 工作台只展示和统筹；真实生成由 agent/CLI 执行。
- 本仓库自带 8 个 skill 和 `mvwb` CLI；不依赖作者的个人目录。

### 依赖

| 能力 | 用哪个 |
|---|---|
| 工作台模板 / DATA 契约 | `zz-mv-factory` |
| 音乐（ACE-Step） | `ace-music` + `zz-runninghub-cli` |
| 资产图提示词（MOSS） | `zz-manju-image-prompts` |
| H3 视频提示词 | `h3-prompt-writing` |
| Muse 提示词 / Router 视频 | `muse-router` |
| RunningHub 提交/轮询/下载 | `zz-runninghub-cli` |
| 粗剪/按歌词对齐 | `zz-mv-trim` |
| Key / 余额 / 本地服务 | `mvwb`（底层 `scripts/mv_keys.py`） |

## 快速开始

```bash
mvwb doctor                 # 检查 Python/ffmpeg/skills/keys
mvwb demo                   # 打开 demo 工作台（无需 Key）
mvwb init my_project        # 从 demo 复制一个工作区
```

- `mvwb demo` 会启动本地服务并打开 `http://127.0.0.1:8776/go`。
- 静态版直接打开 `demo/workbench.html`，没有按钮；服务版右上角才有“配置 Key”。
- 不配 Key：原文、框架、工作台可用；生成会停。

## Key 与余额

- 唯一真源：`~/.config/mv-workbench/keys.json`（目录 0700 / 文件 0600）。
- 两份 key：RunningHub（ACE/MOSS/H3/S2V）、Router（Muse）。
- 推荐在页面里配：`mvwb server` → 右上角“配置 Key” → 两个密码框 → 保存 → 自动刷余额。
- 命令行：

```bash
mvwb keys set runninghub
mvwb keys set router
mvwb keys status
mvwb keys balance --write <workbench.html>
```

- Router 默认 new-api/TokenTech：`https://router.kcacher.top`，`/v1/videos` 异步；2s ≈ ¥1，10s ≈ ¥5。
- 需要改 Router 地址/模式时：`mvwb keys config router --base-url ... --balance-mode newapi`。
- 原始 key 不进入 HTML/DATA/日志；`DATA.keys` 只有掩码和余额。
- 生成命令统一经 `mv_keys.py exec` 注入 key；不要依赖 shell 残留的 `RUNNINGHUB_API_KEY`/`ROUTER_API_KEY`。

## 四步

### Step 1 · 资料

1. 先找 `原文/`、`甲方资料/`、`输入/` 下的歌词/脚本；文件名含 `歌词`、`lyric`、`脚本`、`script`。
2. 找到就只读入库，不改写、不拆行、不“优化”。
3. 没找到：先问用户有没有甲方资料；没有就按产品/故事/人物/风格/时长/参考引导，生成草稿。
4. 原文入库：

```text
workspaces/<project>/
├─ 原文/lyric_original.md   歌名/主歌/副歌，原文
├─ 原文/story_script.md     故事脚本原文，不拆镜
└─ 原文/lyric.json          L01… 行号映射
```

**门：原文确认。** 用户说“没问题/用这版”后锁定；改原文=重新起工作台。

### Step 2 · 空工作台

- 用 `mvwb init <name>` 从 `demo/` 复制，或复制 `templates/workbench.html` + 自己的 `data.json`。
- 构建：

```bash
python3 scripts/build_workbench.py \
  --template templates/workbench.html \
  --data workspaces/<name>/data.json \
  --out workspaces/<name>/workbench.html
```

- `DATA` 结构见 `zz-mv-factory`；最少包含 `meta/lyric/script/keys/mvs`。
- 生成后停下来问：**一次多少条 / 每条多长 / 什么风格**（建议先 5–10 条打样）。
- 打开服务版：`mvwb server --workspace <name>`；静态版直接开 `workbench.html`。

**门：批次参数确认。** 此步不花钱。

### Step 3 · MV 框架（纯文本）

创建 `MV001…MV00N`，每条：

- `mv_manifest.json`：stages 全 `not_started`；genome、cost/spent=0。
- `02_storyboard/storyboard_v1.json`：标准分镜（镜号/对应句/景别/运镜/画面描述/时长），并按关联切视频段（1 段可含 1+ 镜，**≤10s**），`videos: []`。
- `00_framework.md`：音乐计划、资产清单、分镜/视频段表。
- 更新 `DATA.mvs`：音乐/资产为空，分镜有 shots/segments；保留 `keys` 快照。

给用户看框架摘要，问：

> 框架有没有要改的？要改哪条 MV、哪个镜头、哪句？只改你点名的部分。

**门：框架审核通过 + 生成范围/报价确认。**

### Step 4 · 生成内容

#### 4.0 花钱前预检

```bash
mvwb keys status
mvwb keys balance
mvwb quote --model muse-video-ext --seconds 2
```

- 缺 key / 余额不足 / 查询失败：停。
- 报价 = 数量 × 单价；用户确认才跑。

#### 4.1 生成

| 内容 | 命令 | 写入 DATA |
|---|---|---|
| 音乐 | `mvwb rh --app 2075301815628943362 ...` | `detail.music` |
| 资产 | `mvwb rh --app 2116462203997081601 ...` | `detail.assets` |
| H3 视频 | `mvwb rh --wf 2110943749894402050 ...` | `segments[].videos` |
| Muse 视频 | `mvwb muse --prompt "..." --seconds 2 --size 720x1280 --out ...` | `segments[].videos` |
| 粗剪 | `zz-mv-trim` | 不改模板，供剪辑用 |

- 每个视频段可生成多条视频；当前第一条，历史追加。
- 新版本写 `*_v{n+1}.json`，不覆盖。
- 更新 `stages/status/spent`，重建 `DATA`。

#### 4.2 审核

> 生成完了，哪些要改？要改哪条 MV、哪个视频段、哪张图/哪首歌？

- 只重跑点名项；新版本+历史。
- 音乐 `locked` 后不可改；换音乐=新建 MV。
- 用户说“定稿/通过” → 对应 stage `locked`。

## 模型卡（2026-11 实测，价格会变）

| 阶段 | 默认 | 关键限制 | 参考价 | 提示词走 |
|---|---|---|---|---|
| 音乐 | ACE-Step 1.5 `2075301815628943362` | 中文咬字、45s | 39 币/45s | `ace-music` |
| 资产 | MOSS `2116462203997081601` | 2MP、9:16；文字/手易崩 | 26 币/张 | `zz-manju-image-prompts` |
| 视频 H3 | YZ金鱼多参 `2110943749894402050` | 6 图参考；颜色/场景漂 | 约 19 币/4s | `h3-prompt-writing` |
| 视频 Muse | `muse-video-ext`（Router） | 9 图参考、2–10s、720p、原生音频 | 2s≈¥1；10s≈¥5 | `muse-router` |
| 口型 | S2V `1979183169033375745` | 音频驱动、8s、需超分 | 176 币/8s | `h3-prompt-writing` |

- 视频按段确认模型；不同段可不同模型，但同一 MV 的风格包/调色要统一。
- 换模型=新版本；旧产物保留历史。

## 多参参考包

- 当前视频模型都是**多参考图条件生成**，不是首帧 I2V；分镜表没有首帧列。
- 资产阶段只产参考包：角色四视图、场景板、道具/产品实拍。
- 每个视频段 prompt 声明图1..图N职责；一图一职；不超过模型上限。
- 参考图不锁构图/运镜；景别、机位、动作、光线写在 prompt。
- 先跑 1 段样板，检查脸/场景/产品/动作/文字，再批量。

## 音乐先于视频

- 第三步的 shot duration 只是计划；音乐生成后按真实句时长对齐，更新 storyboard/segments。
- 视频依赖音乐时间轴；只选视频不选音乐时，提示先音乐，或确认用计划时长（后续补音乐会令视频过期）。

## 审核/版本/交付

- 第一条/第一个风格包全审；其余抽检。
- QA：H3 颜色/场景；Muse 脸/构图/审核/文字；MOSS 手/文字；ACE 咬字/时长。
- 输出：模型 720p → 成片 1080×1920/30fps、字幕、响度、去模型原声；剪辑另走。
- 成本/账号：报价、并发、429 退避、失败退款；共享 key 未经允许不用。
- 版本：model/workflow/prompt/refs/params/seed/cost/time 落盘；DATA 与源 JSON 同步。
- 合规：模型/音乐/歌词授权；广告法/产品宣称；内容审核；产品图用实拍。

## 文件

```text
skills/
  zz-mv-gongzuotai/      本 skill（四步入口）
  zz-mv-factory/         模板/DATA 契约
  zz-mv-trim/            粗剪
  zz-runninghub-cli/     RunningHub API
  ace-music/             ACE-Step 标签/节点
  h3-prompt-writing/     H3 提示词
  zz-manju-image-prompts/MOSS 提示词
  muse-router/           Muse 提示词 + Router 视频
scripts/
  mvwb.py                CLI
  mv_keys.py             Key/余额/exec
  mv_keys_server.py      本地 Key 配置服务
  build_workbench.py     DATA → workbench.html
  providers/tokentech_video.py  Muse /v1/videos
templates/workbench.html 工作台模板
demo/                    原创 demo
config/                  模型价格/provider 示例
```

## 版本

- v3.0（2026-11-13）：公开打包；APIMart 移除，统一 Router；新增 ace-music/muse-router；`mvwb` CLI；干净 demo；Windows/macOS 安装脚本。
- v2.2：Key 配置服务；v2.1：Key/余额统一；v2.0：四步对话。
