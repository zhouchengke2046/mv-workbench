# 新手先看：这到底是什么、怎么开始

> 给第一次接触 `zz-mv-gongzuotai` 的同学。  
> 先看这一页，再让 agent 读 `SKILL.md`。

## 1. 它不是“双击安装的软件”

它没有安装包、没有“下一步”、没有桌面图标。

它是一个 **给 AI 助手用的工作流技能包**：你把解压后的文件夹交给 WorkBuddy / ZCode 这类 agent，agent 按里面的 `SKILL.md` 带你走完 MV 产线。

所以：

- **没有“哪个 exe 是打开它的”**。解压后不要找 exe。
- **不需要在 WorkBuddy 里选“生成模型”**。你选的是对话用的 agent 模型；音乐/图片/视频模型由 skill 调用。
- **工作台是浏览器里的一个本地网页**，不是软件窗口。用 `mvwb open` 打开，不要双击 `workbench.html`。

## 2. 它会给你什么

每个 MV 一个本地目录：

```text
workspace/
├─ 原文/                你给的歌词、故事脚本
├─ workbench.html       只读工作台（看进度、资产、分镜、视频段）
└─ MV001/
   ├─ 01_music/         音乐 + 每句时间轴
   ├─ 02_assets/        人物/场景/道具参考图
   ├─ 03_segments/      视频段（每段 ≤10s）
   └─ handoff_v1.json   交给剪辑的清单
```

**它不给你成片**：不粗剪、不拼片、不加字幕/混音。视频段交给下一位剪辑。

## 3. 你要准备什么

| 必须 | 说明 |
|---|---|
| 一台电脑 | macOS 或 Windows 都可以 |
| Python 3.9+ | 跑 `mvwb`；agent 可以帮你装 |
| ffmpeg / ffprobe | 读音乐时长、检查视频；没有也能做计划，但时间轴/时长检查会缺 |
| 一个 agent | WorkBuddy、ZCode 或同类；能读写文件、运行命令 |
| 歌词或故事脚本 | 甲方原文即可，不用先拆镜 |
| RunningHub Key | 音乐、资产图、H3 视频用；充值后生成 |
| Router Key | Muse 视频用；充值后生成 |

可选：人物/场景/产品参考图、品牌色、必须出现的产品镜头。

**只看看 demo 不需要 Key。**

## 4. 三种开始方式

### 方式 A：我只想先看看（不花钱）

1. 解压到一个**英文短路径**，例如 `D:\MV\zz-mv-gongzuotai`。
2. 直接双击 `demo/workbench.html`；或者在这个文件夹里运行：

```bash
python scripts/mvwb.py open
```

3. 浏览器会打开一个本地 `file://` 页面，就是 demo 工作台。
4. **不需要启动任何后台服务，也没有终端窗口要一直开着。** 看完直接关网页。

### 方式 B：让 agent 带我做一个项目（推荐）

1. 解压到英文短路径。
2. 在 WorkBuddy / ZCode 里，把**解压后的 `zz-mv-gongzuotai` 文件夹**设为工作区。
   - 不要选它的上一层 `tools` / `Downloads`，否则 agent 找不到 `SKILL.md`。
3. 对 agent 说：

```text
请读取这个文件夹里的 SKILL.md，按 zz-mv-gongzuotai 的流程带我做一个 MV 项目。
先只做原文、空工作台和 MV 框架，不要提交任何生成任务。
```

4. agent 会先问你：做几个 MV、每首多长、什么风格、人物/场景/产品、比例、预算。
5. 框架审核通过后，再配置 Key、生成音乐/资产/视频段。

### 方式 C：安装成全局 skill

```bash
# macOS / Linux
./install.sh
./mvwb doctor

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .\install.ps1
.\mvwb.cmd doctor
```

安装后，agent 在别的项目里也能识别 `zz-mv-gongzuotai`，`mvwb` 也可以全局用。

## 5. 一次完整流程（人话版）

```text
你给歌词/脚本
  → agent 生成空工作台 + MV 框架（不花钱）
  → 你审核框架：人物、场景、分镜、段数、时长
  → 配 Key，看余额，报价
  → 生成音乐（先锁定）
  → 读音乐实际时长，生成时间轴
  → 生成资产图（人物/场景/道具）
  → 逐段生成视频（每段 ≤10s，可多条）
  → 你审核，只重跑点名项
  → 每 MV 出 handoff，交给剪辑
```

关键顺序：**音乐先锁定，再资产，再视频段**。音乐没锁定就生成视频，后面换歌会导致视频段全部重做。

## 6. 你会被问到的参数

| 参数 | 默认/建议 | 说明 |
|---|---|---|
| MV 数量 | 先做 1 条打样 | 不要一上来 100 条 |
| 每首时长 | 30s / 45s / 60s | 这是 `target_duration`，音乐按它生成 |
| 画面比例 | **9:16 竖屏** | 工作台按 1080×1920；Muse 输出 720×1280 |
| 风格 | 先选一个参考包 | 雨夜城市、地铁、街景等 |
| 人物/产品 | 有参考图就给 | 资产图会用它保持一致性 |
| 预算上限 | 先给一个数 | agent 报价后再提交 |

没有特别说明时，按 **9:16 竖屏** 做。

## 7. 要花钱吗？

**不是免费。** 这个项目本身不收费，但调用模型要付给两家服务商：

| 消耗 | 单位 | 参考价（2026-11-13，会变） |
|---|---|---|
| RunningHub 音乐 ACE | 币 | 39 币 / 45s |
| RunningHub 资产 MOSS | 币 | 26 币 / 张 |
| RunningHub 视频 H3 | 币 | 约 19 币 / 4s |
| RunningHub 口型 S2V | 币 | 176 币 / 8s |
| Router Muse 视频 | 人民币 | 2s ≈ ¥1；10s ≈ ¥5 |

- **币** 是 RunningHub 的点数（RunningHub 也有单独的钱包余额）；**余额** 通常指 Router 的人民币账户。两个服务商的钱包分开。
- 一条 45s、4 张资产、8 段视频的 MV，粗算几百币（H3）或几十元（Muse），以账单为准。
- 生成前先 `mvwb quote`，agent 应给你数量 × 单价的报价，你确认后再跑。
- 只做原文、工作台、框架、分镜计划，**不花钱**。

## 8. 最容易卡住的 8 件事

**① 解压后不知道点哪个**
没有可点的入口。看 `START_HERE.md`（本页）；要打开工作台用 `mvwb open`。

**② Windows 解压/路径报错**
解压到 `D:\MV\...` 这类英文短路径，不要放在中文名 + 空格的深层目录。右键“解压到当前文件夹”，不要只双击 zip。

**③ ffmpeg 装不上**
Windows 先试 `winget install Gyan.FFmpeg`；GitHub 超时就换 npm 镜像装 `@ffmpeg-installer/ffmpeg` + `@ffprobe-installer/ffprobe`，把两个 exe 放进一个 PATH 目录。仍不行用 WSL2。

**④ Key 是什么、填哪里**
Key 是充值后生成的令牌，相当于密码。打开终端，运行：

```bash
mvwb keys set runninghub
mvwb keys set router
```

按提示粘贴，输入不回显。配完用 `mvwb keys balance --data <项目>/data.json` 查余额，再 `mvwb build` 刷新页面。
**不要把 Key 发到对话里**；已经发过的，去服务商后台作废重发。

**⑤ 工作台没有“配置 Key”按钮**
这是设计：工作台是纯静态文件，不联网、不配置 Key。Key 用上面的 `mvwb keys set`，页面只显示掩码和余额快照。

**⑥ 资产图/视频是空白框**
先运行：

```bash
mvwb check --data workspaces/my_project/data.json
mvwb build --data workspaces/my_project/data.json --out workspaces/my_project/workbench.html
```

`check` 显示 `缺失/空文件：0` 才正常；有 `[missing]` 就是文件没下载或路径不对。

**⑦ 第一个 MV 做完了，下一个怎么开始**
同一个歌词/项目下，下一个是 `MV002`。对 agent 说：

```text
继续做 MV002，复用已锁定的音乐/资产规则；先出框架，不要直接生成。
```

不同歌词/客户，用 `mvwb init <项目名>` 新建一个 workspace。

**⑧ 为什么不能一键出 100 条**
当前 skill 是**单项目、单 MV 的流水线**：一条一条审核、重跑、锁定。100 条需要在上层做批次和变体规划（风格、人物、场景、镜头节奏、产品露出方式），不是点一下自动复制。先把 1 条打样跑通，再扩批次。

## 9. 术语表

| 词 | 意思 |
|---|---|
| 工作台 | 浏览器里的只读页面，看 MV 进度和产物 |
| 资产图 | 人物/场景/道具参考图，用来保持多条视频一致 |
| 分镜 | 每个镜头对应哪句歌词、景别、运镜、画面描述 |
| 视频段 | 一条 ≤10s 的视频，可含 1 个或多个镜头 |
| 时间轴 | 每句歌词在音乐里的起止秒 |
| handoff | 交给剪辑的段清单：文件、时长、歌词行、音乐起止 |
| Key | 服务商 API 令牌，不是登录密码 |
| 币 / 余额 | RunningHub 点数（另有钱包余额） / Router 人民币账户 |

## 10. 你适合用它吗

适合：愿意用 agent、能按步骤审核、接受“先打样再批量”的团队。

不适合：想要一个双击即用、自动出成片的桌面软件；或者完全不想接触 Key、余额、命令行的人。

---

下一步：让 agent 读 `SKILL.md`；遇到具体报错，把**报错原文 + 你执行的命令 + 截图**发给 agent，不要只说“有 bug”。
