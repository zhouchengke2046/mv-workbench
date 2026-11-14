# zz-mv-gongzuotai

**一个 skill 统筹整条 MV 产线：** 甲方歌词/脚本 → 静态工作台 → 每 MV 的音乐/资产/视频段 → handoff 给剪辑。

> 最终产物到**视频段**结束，不做粗剪、不拼成片。

## 拿到压缩包后怎么开始

1. 解压到英文短路径，例如 `D:\MV\zz-mv-gongzuotai`。
2. **只看工作台**：双击 `demo/workbench.html`。不需要启动服务、不占端口。想配 Key/安装命令，进 `start/` 文件夹。
3. **做自己的项目**：把解压后的文件夹设为 agent（WorkBuddy / ZCode）的工作区，对它说：

```text
请读取这个文件夹里的 SKILL.md，按 zz-mv-gongzuotai 的流程带我做一个 MV 项目。
先只做原文、空工作台和 MV 框架，不要提交任何生成任务。
```

4. 没有 exe、没有“下一步”，这是正常的：它是给 agent 用的 skill 包，不是桌面软件。

> 命令里的 `mvwb` 指安装后的命令；没有安装就在解压目录运行 `python scripts/mvwb.py ...` 或双击 `start/` 里的对应文件。

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.9+ | 跑 `mvwb`、Key 管理、构建器；只用标准库 |
| ffmpeg + ffprobe | 读音乐时长、生成时间轴、检查视频 |
| 一个 agent | WorkBuddy / ZCode / 同类；能读写文件、运行命令 |
| Router Key（必配） | 音乐/资产/视频统一入口；默认 `https://router.kcacher.top` |
| RunningHub / APIMart Key（备用） | Router 连续失败时由老师另发，直连兜底 |

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
- **老师统一发放**：初期只发 Router Key——`zz-keys.json` 里只有 `{"router":"..."}`；放到项目根目录，对 agent 说“导入项目里的 zz-keys.json，导入后删除”。agent 运行：
  ```bash
  mvwb keys import --file workspaces/<project>/zz-keys.json --delete-source
  ```
  文件只要两个字段：`{"runninghub":"...","router":"..."}`；格式见 `references/key-distribution.md`；导入一次全局生效。
- **在工作台配置**：双击 `workbench.html` → 右上角“配置 Key” → 填两个 Key → 下载 `mv-keys-import.json`；对 agent 说“导入下载目录的 mv-keys-import.json”。agent 运行：
  ```bash
  mvwb keys import --file ~/Downloads/mv-keys-import.json --delete-source
  ```
- **备用 Key 走 B001 提醒**：Router 连续失败时 agent 会输出 `[提醒] B001` 块；学生把提醒原文发给老师，由老师决定是否发放备用 `zz-keys.json`。代码表见 `references/alerts.md`。
- **或双击** `start/setup-keys.command`（macOS）/ `start/setup-keys.cmd`（Windows），按提示粘贴两个 Key。
- 或终端：`mvwb keys set runninghub`、`mvwb keys set router`。
- 余额：`mvwb keys balance --data <data.json>`，再 `mvwb build` 刷新页面快照。
- 原始 Key 不进 HTML/DATA/日志/截图；页面只显示掩码和查询时间。下载的导入文件含原始 Key，导入后必须删除。
- **不要把 Key 发到对话里**；已经发过的，去服务商后台作废重发。

## 工作台

- 单文件静态 HTML，双击 / `file://` 打开；不启动服务、不开端口、不联网。
- 顶部显示 Key 掩码和余额快照；右上角“配置 Key”只在本机填 Key、下载导入文件，不联网、不写页面。
- 左侧：歌词/脚本 + MV 列表；右侧：音乐、资产图、分镜/视频段。
- 页面本身只读；生成和更新由 agent 写文件 + `mvwb build` 完成。

## 费用

| 消耗 | 服务商价 | 折合人民币（演示汇率） |
|---|---|---|
| ACE 音乐 | 39 币 / 45s | ≈¥3.9 / 45s |
| MOSS 资产 | 26 币 / 张 | ≈¥2.6 / 张 |
| H3 视频 | 约 19 币 / 4s | ≈¥1.9 / 4s |
| S2V 口型 | 176 币 / 8s | ≈¥17.6 / 8s |
| Muse 视频 | ¥0.5 / s | ¥0.5 / s |

- RunningHub 币→人民币汇率在 `config/models.json` 的 `fx.rh_coin`（示例 0.1），由老师按实际充值比例修改。
- 工作台顶部只显示 Router 余额；所有成本一律折算成 ¥ 展示。

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
用英文路径；命令在 `start/`（`start/mvwb.cmd`）；不强制 0600。路径/权限问题用 WSL2。

## 目录（归类说明）

```text
zz-mv-gongzuotai/
│
│ 给「人」的
├─ README.md                 ← 先看这个（含目录地图）
├─ start/                    ← 入口：安装、mvwb 命令、一键配 Key
│  ├─ setup-keys.command/.cmd   双击配 Key（Mac/Win）
│  ├─ install.sh / install.ps1  安装成全局 skill + mvwb 命令
│  └─ mvwb / mvwb.cmd           未安装时直接用
├─ demo/workbench.html       ← 开箱 demo（双击看效果）
├─ workspaces/<项目>/         ← 你的项目：工作台 + MV001(音乐/资产/视频段)
│
│ 给「agent」的
├─ SKILL.md                  agent 入口（工作区指向这里）
├─ scripts/                  mvwb、keys、alerts、build、timeline、providers
├─ references/               规则契约 / 提醒代码表 / 提示词库 / 平台接口
├─ templates/ + contracts/   工作台模板与数据契约
├─ config/                   zz-keys.example.json、模型价格与 fx 汇率
│
│ 给「开发者」的
├─ tests/  dev/  docs/  .github/
└─ LICENSE  NOTICE.md
```

## License

MIT。见 `LICENSE`。
