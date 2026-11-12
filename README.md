# MV Gongzuotai

**一个 skill 统筹整条 MV 产线：** 甲方歌词/脚本 → 静态 workbench → 每 MV 的音乐/资产/视频段 → handoff 给剪辑。

> 面向能运行本地命令的 agent（ZCode / Claude Code / 同类 skill 宿主）。最终产物到**视频段**结束，不做粗剪、不拼成片。

![demo](docs/workbench.png)

## 这是什么

- **一个入口 skill**：`mv-gongzuotai`，负责整个 MV 项目的四步流程、审核和版本。
- **每个 MV 一个目录**：音乐、资产图、视频段都放在 `MVxxx/` 下。
- **流程到视频段结束**：不粗剪、不做字幕/混音/成片；视频段 + `handoff` 交给剪辑。
- **审核重跑**：每次生成可提修改意见，只重跑点名项，新版本保留历史。
- **Key 配置**：服务版右上角“配置 Key”，只写本地 `keys.json`；原始 Key 不进 HTML/DATA。

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.9+ | 只用标准库；`mvwb` / Key 服务 / 构建器 |
| ffmpeg + ffprobe | 读取音乐时长/时间轴、检查视频时长；macOS `brew install ffmpeg`，Windows `winget install Gyan.FFmpeg`，Ubuntu `sudo apt install ffmpeg` |
| 一个 agent | 能读 skill、运行本地命令、读写文件 |
| RunningHub API Key | ACE/MOSS/H3/S2V |
| Router API Key | Muse；默认 `https://router.kcacher.top` |

**不配 Key 也能用**：原文、工作台、MV 框架、分镜/视频段计划都能生成；只有真正提交模型时才需要 Key。

## 安装

### macOS / Linux

```bash
git clone https://github.com/zhouchengke2046/mv-workbench.git
cd mv-workbench
./install.sh
./mvwb doctor
```

- 安装成一个 skill：`~/.agents/skills/mv-gongzuotai/`。
- 命令：`~/.local/bin/mvwb`；不在 PATH 就直接跑 `./mvwb`。
- Key 文件：`~/.config/mv-workbench/keys.json`（0600）。

### Windows

```powershell
git clone https://github.com/zhouchengke2046/mv-workbench.git
cd mv-workbench
powershell -ExecutionPolicy Bypass -File .\install.ps1
.\mvwb.cmd doctor
```

- skill 安装到 `%USERPROFILE%\.agents\skills\mv-gongzuotai`。
- `mvwb.cmd` 在 `%USERPROFILE%\.local\bin`；加入 PATH，或直接用 `.\mvwb.cmd`。
- 建议 clone 到英文路径；Windows 不强制 `0600`，Key 仍只存本地文件。遇到路径/权限问题用 WSL2。

### 其他 agent

```bash
./install.sh --target /path/to/your/skills/mv-gongzuotai
```

## 压缩包 / 离线使用

Release 里提供 `mv-gongzuotai-v0.2.4-runtime.zip`（运行时精简包，不含 tests/.github/dev 配置），解压后目录是 `mv-gongzuotai/`。

### 方式 A：直接放进 skills（agent 立即识别）

```bash
unzip mv-gongzuotai-v0.2.4-runtime.zip -d ~/.agents/skills/
cd ~/.agents/skills/mv-gongzuotai
./mvwb doctor
./mvwb open
```

- skill 已被 agent 识别；`mvwb` 是文件夹内命令。
- 想全局用 `mvwb`：把 `~/.agents/skills/mv-gongzuotai` 加到 PATH，或按方式 B 安装。

### 方式 B：解压后安装（推荐，生成全局 mvwb）

```bash
unzip mv-gongzuotai-v0.2.4-runtime.zip -d ~/Downloads
cd ~/Downloads/mv-gongzuotai
./install.sh
mvwb doctor
```

Windows：

```powershell
Expand-Archive mv-gongzuotai-v0.2.4-runtime.zip -DestinationPath "$HOME\Downloads"
cd "$HOME\Downloads\mv-gongzuotai"
powershell -ExecutionPolicy Bypass -File .\install.ps1
.\mvwb.cmd doctor
```

> 严格说不是“双击解压就完事”：解压到 skills 目录 = agent 可识别；要全局 `mvwb` 命令，需要 `install.sh` 或手动加 PATH。推荐方式 B。

## 30 秒 demo

```bash
./mvwb open
```

`mvwb open` 会自动启动/复用服务版并打开 `http://127.0.0.1:8776/go`。Demo 使用原创虚构歌词/脚本和 SVG 占位资产，不含客户内容。

静态只读分享（不要用来配 Key）：

```bash
open demo/workbench.html
```

> 静态 `file://` 没有“配置 Key”按钮；要配 Key / 刷余额，用 `./mvwb open` 的服务版。

## 每个 MV 的产物

```text
workspaces/<project>/
├─ 原文/
│  ├─ lyric_original.md
│  ├─ story_script.md
│  └─ lyric.json
├─ workbench.html
└─ MV001/
   ├─ mv_manifest.json
   ├─ 00_framework.md
   ├─ 01_music/
   │  ├─ song_v1.mp3
   │  └─ timeline_v1.json
   ├─ 02_assets/
   │  ├─ assets_v1.json
   │  ├─ role_xxx.png
   │  ├─ scene_xxx.png
   │  └─ prop_xxx.png
   ├─ 03_segments/
   │  ├─ segments_v1.json
   │  ├─ G1_v1.mp4
   │  ├─ G1_v2.mp4      审核重跑的历史
   │  └─ G2_v1.mp4 …
   └─ handoff_v1.json   交给剪辑
```

`handoff_v1.json`：

```json
{
  "mv_id": "MV001",
  "status": "ready",
  "music": "01_music/song_v1.mp3",
  "timeline": "01_music/timeline_v1.json",
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

### 1. 原文

把甲方歌词/脚本放进 `原文/`：

```text
原文/lyric_original.md   歌名/主歌/副歌，原文
原文/story_script.md     故事脚本原文，不拆镜
原文/lyric.json          L01… 行号映射
```

没有甲方资料时，agent 会先问，再按产品/故事/人物/风格/时长/参考引导起草。

### 2. 空工作台

```bash
./mvwb init my_project
# 替换 workspaces/my_project/原文/，让 agent 生成空工作台
```

Agent 用 `templates/workbench.html` + `DATA.json` 构建：

```bash
python3 scripts/build_workbench.py \
  --template templates/workbench.html \
  --data workspaces/my_project/data.json \
  --out workspaces/my_project/workbench.html
```

打开：

```bash
./mvwb open --workspace my_project
```

然后问：**一次多少条 / 每条多长 / 什么风格**。

### 3. MV 文本框架

Agent 生成 `MV001…MV00N`：音乐计划、资产清单、标准分镜、视频段（≤10s）。此时不花钱。审核框架，只改点名处。

### 4. 生成与审核

```bash
./mvwb keys status
./mvwb keys balance
./mvwb quote --model muse-video-ext --seconds 2

# 音乐
./mvwb rh --app 2075301815628943362 --name song_v1 --overrides ov.json --out MV001/01_music

# 时间轴
./mvwb timeline 原文/lyric.json MV001/01_music/song_v1.mp3 --out MV001/01_music

# 资产
./mvwb rh --app 2116462203997081601 --name assets --overrides ov.json --out MV001/02_assets

# 视频段（H3）
./mvwb rh --wf 2110943749894402050 --name G1 --nodes nodes.json --out MV001/03_segments

# 视频段（Muse）
./mvwb muse --prompt "..." --seconds 6 --size 720x1280 --out MV001/03_segments/G1_v1.mp4
```

- 音乐先锁定；资产按参考包；视频段逐段生成。
- 每次审核修改只重跑点名项，写 `v2`，旧版保留。
- 所有段 `locked` 后写 `handoff_v1.json`，项目结束。

## 时长：用户目标 vs 音乐实际

| 时长 | 谁定 | 用途 |
|---|---|---|
| `target_duration` | 用户在第 2 步设定（如 45s） | 音乐请求秒数、总目标时长、预算/段数、框架计划 |
| `actual_duration` / `timeline_v1.json` | 音乐生成后读取 | 分镜/视频段实际时长、Muse `seconds`、H3 帧数、handoff |

- **总时长按用户设定**：ACE 的 `116:value` 用 `target_duration`，框架/段数/预算都按它规划。
- **每段时长按音乐实际**：音乐出来后读实际 `duration/timeline`，更新分镜/段的 `duration`；视频按实际句长生成。
- 实际与目标差 >1s 或 >2% 时暂停，让用户选「接受实际 / 重生成音乐 / 后期裁」。
- 只选视频没音乐：先用 `target_duration` 做 provisional 计划；补音乐后视频段标记 `stale`。

## 模型与价格（2026-11-13，会变）

| 模型 | 用途 | 价格 | 参考 |
|---|---|---|---|
| ACE-Step 1.5 | 音乐 | 39 币/45s | `references/prompts/ace.md` |
| MOSS | 资产图 | 26 币/张 | `references/prompts/moss.md` |
| H3 YZ 多参 | 视频 | 约 19 币/4s | `references/prompts/h3.md` |
| Muse `muse-video-ext` | 视频 | **2s ≈ ¥1；10s ≈ ¥5** | `references/prompts/muse.md` |
| S2V | 口型 | 176 币/8s | `references/prompts/h3.md` |

- 以服务商账单为准；`./mvwb quote` 只是估算。
- 共享/企业 key 未经账号所有者允许不要用。

## 目录

```text
mv-workbench/                ← 一个 skill
├─ SKILL.md                  唯一入口
├─ mvwb / mvwb.cmd
├─ install.sh / install.ps1
├─ scripts/
│  ├─ mvwb.py
│  ├─ mv_keys.py / mv_keys_server.py / mv_keys_ui.js
│  ├─ build_workbench.py
│  ├─ timeline.py
│  └─ providers/
│     ├─ runninghub.py
│     └─ tokentech_video.py
├─ references/
│  ├─ workbench-contract.md
│  ├─ review-and-versions.md
│  ├─ handoff.md
│  ├─ lyrics.md
│  ├─ prompts/ace.md, h3.md, moss.md, muse.md
│  └─ providers/runninghub.md, router.md
├─ templates/workbench.html
├─ contracts/
├─ demo/
├─ config/
├─ tests/
└─ docs/
```

## Key

- 唯一真源：`~/.config/mv-workbench/keys.json`（0600）。
- 页面配置：`./mvwb open` → 右上角“配置 Key” → RunningHub / Router。
- 命令行：`./mvwb keys set runninghub`、`./mvwb keys set router`。
- 原始 Key 不进 HTML/DATA/日志/截图。
- 生成命令统一经 `mv_keys.py exec` 注入；不要依赖 shell 残留 Key。

## 安全

- Key 配置服务只绑 `127.0.0.1`；POST 校验 Origin/Content-Type；静态版不加载接口。
- 无遥测、无云端同步；工作台和产物都在本地。
- **不要把客户歌词/脚本/素材提交到公开仓库**；本仓库 demo 是原创虚构内容。

## 常见问题

**页面没有“配置 Key”按钮 / 点不动？**  
先 `./mvwb status`，再 `./mvwb open`。只认它打印的 `http://127.0.0.1:8776/go`；`file://` 静态版没有按钮。Console 里 `document.documentElement.dataset.mvMode` 应为 `service`。

**Router 域名打不开？**  
用 `https://router.kcacher.top`，不要用 `router.kbtech.app`。

**401 / 无效令牌？**  
Key 错/过期/分组无权限；`./mvwb keys status` 看掩码，`./mvwb keys balance` 看错误。

**429 / 503？**  
限流或渠道未启用；退避重试，不要死循环提交。

**余额不对？**  
Router 2s 实测 ¥1；RunningHub 扣 RH 币，和钱包分开；以账单为准。

**ffmpeg 找不到？**  
安装 ffmpeg 后 `./mvwb doctor`。

**macOS 和 Windows 有区别吗？**  
核心 Python/CLI 跨平台；差异在安装脚本、`mvwb.cmd` vs `mvwb`、ffmpeg 安装、Windows 不强制 0600。建议 Windows 用英文路径或 WSL2。

## 已知限制

- Muse 参考图字段尚未验证（`image_urls` / `input_reference` / 单个 `image`）；当前只验证文本生视频 2s。
- Muse 10s 未实测；2s 实测 720×1280/24fps。
- ACE/MOSS/H3/S2V 的实测来自 RunningHub 账号；换账号/工作流版本需重验。
- 不做粗剪/成片；剪辑在外部。
- Windows 只做了兼容设计和 CI 冒烟，未在干净 Windows 全量跑过；建议 WSL2。
- 价格/工作流 ID 会变；以 `config/models.json` 的 `as_of` 和服务商为准。

## 开发 / 测试

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
python3 scripts/build_workbench.py --data demo/data.json --out demo/workbench.html
node --check scripts/mv_keys_ui.js
python3 scripts/check_secrets.py
```

- 测试不调用真实付费 API；用 mock server。
- CI：Ubuntu 22.04/24.04、macOS、Windows + Python 3.9/3.11。

## License

MIT。第三方归属见 [NOTICE.md](NOTICE.md)。
