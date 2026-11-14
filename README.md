# zz-mv-gongzuotai

**一个 skill 统筹整条 MV 产线：** 甲方歌词/脚本 → 静态工作台 → 每 MV 的音乐/资产/视频段 → handoff 给剪辑。

> 最终产物到**视频段**结束，不做粗剪、不拼成片。

## 拿到压缩包后怎么开始

1. 解压到英文短路径，例如 `D:\MV\zz-mv-gongzuotai`。
2. **只看工作台**：双击 `demo/workbench.html`。不需要启动服务、不占端口。
3. **做自己的项目**：把解压后的文件夹设为 agent（WorkBuddy / ZCode）的工作区，对它说：

```text
请读取这个文件夹里的 SKILL.md，按 zz-mv-gongzuotai 的流程带我做一个 MV 项目。
先只做原文、空工作台和 MV 框架，不要提交任何生成任务。
```

4. 没有 exe、没有“下一步”，这是正常的：它是给 agent 用的 skill 包，不是桌面软件。

> 命令里的 `mvwb` 指安装后的命令；没有安装就在解压目录运行 `python scripts/mvwb.py ...`。

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.9+ | 跑 `mvwb`、Key 管理、构建器；只用标准库 |
| ffmpeg + ffprobe | 读音乐时长、生成时间轴、检查视频 |
| 一个 agent | WorkBuddy / ZCode / 同类；能读写文件、运行命令 |
| RunningHub Key | ACE 音乐、MOSS 资产、H3 视频、S2V 口型 |
| Router Key | Muse 视频；默认 `https://router.kcacher.top` |

不配 Key 也能做原文、工作台、MV 框架和分镜计划；只有提交模型才需要 Key。

## 四步

```text
原文 → 空工作台 → MV 文本框架 → 生成与审核（音乐→资产→视频段）→ handoff
```

- **原文**：歌词/脚本原样保存，生成 `L01…` 行号。
- **空工作台**：每个 MV 一个目录，`data.json` + 静态 `workbench.html`。
- **文本框架**：音乐计划、资产清单、分镜、视频段（≤10s）；先审核再花钱。
- **生成**：音乐先锁定，再资产，再视频段；只重跑点名项，新版本保留历史。
- **交付**：所有段 `locked` 后写 `handoff_v1.json`，剪辑拿视频段和清单进入下一阶段。

每步的输入、产物、自检和门见 `references/step-contract.md`。  
角色/风格提示词见 `references/prompts/casting-style.md`；变体与去重见 `references/variation.md`。

## 常用命令

```bash
mvwb doctor
mvwb open
mvwb open --workspace my_project
mvwb init my_project
mvwb keys status
mvwb keys set runninghub
mvwb keys set router
mvwb keys balance --data workspaces/my_project/data.json
mvwb quote --model muse-video-ext --seconds 6
mvwb build --data workspaces/my_project/data.json --out workspaces/my_project/workbench.html
mvwb check --data workspaces/my_project/data.json
mvwb rh --app <id> --name <tag> --overrides <json> --out <dir>
mvwb rh --wf <id> --name G1 --nodes nodes_G1.json --out MV001/03_segments
mvwb muse --prompt "..." --seconds 6 --size 720x1280 --out MV001/03_segments/G1_v1.mp4
mvwb timeline <lyric.json> <audio.mp3> --out MV001/01_music
```

## Key

- 唯一真源：`~/.config/mv-workbench/keys.json`（macOS/Linux 0600）。
- **最简单**：双击 `setup-keys.command`（macOS）/ `setup-keys.cmd`（Windows），按提示粘贴两个 Key，输入不回显。
- 或终端：`mvwb keys set runninghub`、`mvwb keys set router`。
- 余额：`mvwb keys balance --data <data.json>`，再 `mvwb build` 刷新页面快照。
- 原始 Key 不进 HTML/DATA/日志/截图；页面只显示掩码和查询时间。
- **不要把 Key 发到对话里**；已经发过的，去服务商后台作废重发。

## 工作台

- 单文件静态 HTML，双击 / `file://` 打开；不启动服务、不开端口、不联网。
- 顶部只显示 Key 掩码和余额快照；没有“配置 Key”按钮是设计。
- 左侧：歌词/脚本 + MV 列表；右侧：音乐、资产图、分镜/视频段。
- 只读；生成和更新由 agent 写文件 + `mvwb build` 完成。

## 费用

| 消耗 | 参考价（2026-11-13，会变） |
|---|---|
| ACE 音乐 | 39 币 / 45s |
| MOSS 资产 | 26 币 / 张 |
| H3 视频 | 约 19 币 / 4s |
| S2V 口型 | 176 币 / 8s |
| Muse 视频 | 2s ≈ ¥1；10s ≈ ¥5 |

- 以服务商账单为准；`mvwb quote` 只是估算。
- 生成前先报价（数量 × 单价），用户确认后才提交。

## 常见问题

**工作台怎么打开？需要服务吗？**  
不需要。双击 `workbench.html`，或 `mvwb open [--workspace NAME]`；只是用浏览器打开本地文件。

**资产图/视频空白？**  
`mvwb check --data ...` 有 `[missing]` 就修路径或重新生成；全 0 还空白就 `mvwb build` 后强制刷新。

**Key 可以发到对话里吗？**  
不可以。让用户在终端运行 `mvwb keys set ...`，输入不回显。

**ffmpeg 装不上？**  
Windows 先试 `winget install Gyan.FFmpeg`；下载超时就换 npm 镜像装 `@ffmpeg-installer/ffmpeg` + `@ffprobe-installer/ffprobe`，或 WSL2。

**Windows 要注意什么？**  
用英文路径；命令用 `mvwb.cmd`；不强制 0600。路径/权限问题用 WSL2。

## 目录

```text
zz-mv-gongzuotai/
├─ SKILL.md                  唯一入口（给 agent）
├─ README.md                 本文件
├─ mvwb / mvwb.cmd
├─ setup-keys.command / setup-keys.cmd
├─ install.sh / install.ps1
├─ scripts/                  mvwb、keys、build、timeline、providers
├─ references/               契约、审核、handoff、提示词、供应商
├─ templates/workbench.html
├─ contracts/
├─ demo/                     可直接打开的 demo
└─ config/
```

## License

MIT。见 `LICENSE`。
