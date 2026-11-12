# RunningHub CLI 薄适配层（原 zz-rhcli）

> 2026-10-29 并入 `zz-runninghub-cli`。以下保留原文；`{baseDir}` = 本 skill 目录，`{UPSTREAM}` 定义见下。
> B 站工作流发现见 `references/discover-bilibili.md`。


本技能**唯一职责**：把 RunningHub CLI 调用能力吃透，并且越用越好用。不复制任何官方代码 —— 指路上游脚本，加一层自进化记忆（习惯 + 工作流目录），官方一更新一个 `git pull` 即可同步，永不落后。

B 站发现等外部来源发现功能见 `references/discover-bilibili.md`。

## 上游（唯一事实源）

官方 skill 仓库 clone 在 `~/TraeWork/runninghub-upstream/`，其下 `runninghub/` 为官方 skill 本体。
以下用 `{UPSTREAM}` 指代 `<克隆目录>/runninghub`。

> ⚠️ **路径会漂移**：该目录历史上在 `~/TraeWork/`，现已迁至 `~/github/runninghub-upstream/`。
> `scripts/rh_profile.py` 已改为**候选列表自动探测**（`~/TraeWork/…` → `~/github/…`），不需手动改代码；
> 若两者都不是你的实际位置，用环境变量 `RH_UPSTREAM_DIR` 显式指定。

```bash
# 首次安装（推荐放在 ~/github/ 下）：
git clone --depth 1 https://github.com/HM-RunningHub/OpenClaw_RH_Skills ~/github/runninghub-upstream
# 更新（官方发版后执行一次）：
git -C ~/github/runninghub-upstream pull
```

## 四个入口

| 入口 | 位置 | 作用 |
|------|------|------|
| 标准模型 CLI | `{UPSTREAM}/scripts/runninghub.py` | 420 端点：图/视频/音频/3D/理解，`--task` 语义路由 |
| AI 应用 CLI | `{UPSTREAM}/scripts/runninghub_app.py` | 浏览 / 查节点 / 运行 ComfyUI 工作流 |
| SDK 补齐 CLI | `{baseDir}/scripts/rh_sdk.py` | **23 个子命令**：取消任务 / 查工作流JSON / LoRA上传 / workflow直传 / 账户 / 队列 / 状态 / 结果 / 下载 / 复制 / 模型 / 价格 / 链式修改运行 / 自动等待 / 手机号登录 / 输出历史 / 调用日志 / Webhook调试 / API Key管理 / 门户模板 / 标准模型调用（依赖 `runninghub-sdk`） |
| 自进化记忆 | `{baseDir}/scripts/rh_profile.py` | 习惯 + 工作流目录 + 成功率/质量/成本/失败经验沉淀，存 `~/.runninghub/profile.json`，**所有 Agent 共享** |

## 关键规则（Trae 适配，覆盖官方默认）

1. 一律走脚本，禁止直接 curl。
2. **视频/图片生成前**：先读官方模型菜单 `{UPSTREAM}/references/video-models.md`、`image-models.md`，按官方规则展示菜单、等用户选择。
3. 输出到 `/tmp/rh-output/`；交付用脚本打印的 `OUTPUT_FILE:<路径>` 直接引用本地文件，**不展示 runninghub.cn 内部 URL**（用户打不开）。
4. 慢任务（视频/AI 应用/3D/音乐）执行前先通知"开始生成啦，需要几分钟，请稍等～"。
5. 简短中文提示词 → 增强为详细英文再发送。
6. 脚本打印 `COST:¥X.XX` → 回复带一句"花了 ¥X.XX"。

## API Key

```bash
export RUNNINGHUB_API_KEY="你的key"        # 每台 Agent 都要配（写入 ~/.zshrc 持久化）
python3 {UPSTREAM}/scripts/runninghub.py --check
```

本项目统一由 `mvwb`/`mv_keys.py exec` 注入 `RUNNINGHUB_API_KEY`；不要依赖其他客户端配置文件里的 key。

## 依赖安装

```bash
pip3 install runninghub-sdk    # rh_sdk.py 的依赖（23 个子命令）
```

`rh_profile.py` 纯标准库零依赖，无需安装。

## 上游路径可配置

`scripts/rh_profile.py` 按以下顺序解析上游目录：

1. 环境变量 `RH_UPSTREAM_DIR`
2. 候选路径中第一个存在的目录：`~/TraeWork/runninghub-upstream/runninghub` → `~/github/runninghub-upstream/runninghub`
3. 以上都不存在时退回第 2 项的第一个（便于报错时定位）

一般无需配置。位置特殊时才需要覆盖：

```bash
export RH_UPSTREAM_DIR="/your/path/to/runninghub"   # 覆盖 rh_profile.py 的上游路径
```

## 用法（命令与官方一致，完整说明看官方 SKILL.md / references）

```bash
# 标准生成：语义路由（最省心）或指定端点
python3 {UPSTREAM}/scripts/runninghub.py --task text-to-video --prompt "..." -o /tmp/rh-output/x.mp4
python3 {UPSTREAM}/scripts/runninghub.py --endpoint <EP> --prompt "..." --param k=v [--image P] -o /tmp/rh-output/x.png
python3 {UPSTREAM}/scripts/runninghub.py --list [--type image|video|audio|3d|string] [--task T]
python3 {UPSTREAM}/scripts/runninghub.py --info <EP>

# AI 应用
python3 {UPSTREAM}/scripts/runninghub_app.py --list [--sort RECOMMEND|HOTTEST|NEWEST] [--size N]
python3 {UPSTREAM}/scripts/runninghub_app.py --info <WEBAPP_ID>
python3 {UPSTREAM}/scripts/runninghub_app.py --run <WEBAPP_ID> --node "52:prompt=xxx" --file "39:image=/tmp/a.jpg" -o /tmp/rh-output/r.png

# 自进化（习惯跨 Agent 共享）
python3 {baseDir}/scripts/rh_profile.py get                       # 读偏好 → 作本次默认值
python3 {baseDir}/scripts/rh_profile.py record <EP> --task <T> [--status success|failed] [--cost F] [--quality 1-5]
                                                                 # 每次调用后记录（成功/失败/成本/质量 → 影响 suggest 排序与降级）
python3 {baseDir}/scripts/rh_profile.py set duration 10           # 用户说"以后都…"时固化（key: video_model/image_model/duration/aspect_ratio/cost_pref/lang）
python3 {baseDir}/scripts/rh_profile.py alias 海螺 <EP>            # 用户昵称 → 端点
python3 {baseDir}/scripts/rh_profile.py suggest <task> --top 3    # 语义选型（成功率+质量+成本+熟悉度+流行度，读上游 capabilities.json）

# SDK 补齐（23 个子命令，覆盖 SDK 全部能力）
python3 {baseDir}/scripts/rh_sdk.py cancel <taskId>                              # 取消任务（避免空耗 RH 币）
python3 {baseDir}/scripts/rh_sdk.py workflow-json <workflowId> [--parsed]        # 获取工作流 API 格式 JSON
python3 {baseDir}/scripts/rh_sdk.py upload-lora <filePath>                        # 上传 LoRA（三步链自动完成）
python3 {baseDir}/scripts/rh_sdk.py run-workflow-json <jsonPath> [--node "N:F=V"] # 本地 workflow JSON 直传运行
python3 {baseDir}/scripts/rh_sdk.py account                                        # 账户详情（余额/RH币/运行任务/队列）
python3 {baseDir}/scripts/rh_sdk.py queue                                          # 队列状态
python3 {baseDir}/scripts/rh_sdk.py status <taskId>                                # 查询任务状态
python3 {baseDir}/scripts/rh_sdk.py outputs <taskId>                               # 获取任务结果文件
python3 {baseDir}/scripts/rh_sdk.py download <taskId> -o <dir>                      # 下载结果到本地
python3 {baseDir}/scripts/rh_sdk.py copy-workflow <workflowId>                     # 复制工作流到自己账号
python3 {baseDir}/scripts/rh_sdk.py models                                         # 列出公共模型
python3 {baseDir}/scripts/rh_sdk.py price <modelId>                               # 预览模型价格
python3 {baseDir}/scripts/rh_sdk.py run-with-modifier <workflowId> \             # 链式修改参数运行（推荐）
    --text "6:a girl" --seed "3:123" --steps "3:20" --image "14:/tmp/a.jpg" --wait
python3 {baseDir}/scripts/rh_sdk.py wait <taskId> [--timeout 300]                # 自动轮询等待完成
python3 {baseDir}/scripts/rh_sdk.py login <phone> <password>                      # 手机号登录获取用户 Token
python3 {baseDir}/scripts/rh_sdk.py history [--status SUCCESS] [--task-name X]    # 查询输出历史
python3 {baseDir}/scripts/rh_sdk.py download-history --size 30 -o <dir>           # 批量下载历史输出
python3 {baseDir}/scripts/rh_sdk.py call-log <taskId> <userId>                    # 查调用日志详情（排查失败）
python3 {baseDir}/scripts/rh_sdk.py webhook-detail <taskId>                       # 查 webhook 事件详情
python3 {baseDir}/scripts/rh_sdk.py webhook-retry <webhookId> <webhookUrl>       # 重试 webhook 事件
python3 {baseDir}/scripts/rh_sdk.py api-keys                                       # 列出所有 API Key
python3 {baseDir}/scripts/rh_sdk.py validate-key                                   # 验证当前 API Key
python3 {baseDir}/scripts/rh_sdk.py templates [--sort HOTTEST] [--search X]       # 浏览门户精选模板
python3 {baseDir}/scripts/rh_sdk.py run-model <endpoint> --prompt "..." [--wait] # SDK 调用标准模型 API
```

**自进化闭环**：任务前 `get` 读偏好作默认值 → 执行生成 → `record`（status/cost/quality 全量记录，**失败也记**）→ 用户表达稳定偏好 `set` / `alias` → 语义选型不确定时 `suggest`（综合分：成功率 40% + 质量 30% + 成本反向 20% + 熟悉度 10%，失败率 ≥50% 打五折，全失败的端点自动沉到未用过的端点后面）。隐私边界：只记习惯与调用结果，禁止写入密钥/对话原文/敏感信息。

## 工作流目录（curated registry，自进化的一部分）

**平台没有关键词搜索 API**（实测 `title`/`keyword` 参数均被忽略），只能靠 RECOMMEND/HOTTEST/NEWEST 排序浏览。因此沉淀手段 = **自建工作流目录**（存在 `~/.runninghub/profile.json` 的 `workflows` 域，跨 Agent 共享，越用越准）。

用户要"找个能做 X 的工作流 / 有什么好用的应用"且没给链接时，按此飞轮：

1. `python3 {baseDir}/scripts/rh_profile.py workflow search X` — 先查自建目录，命中直接给 webappId
2. 未命中 → `{UPSTREAM}/scripts/runninghub_app.py --list --sort HOTTEST [--size 10]` 或 `--sort NEWEST` 浏览（标题/描述人工筛选候选）
3. 候选用 `--info <webappId>` 确认输入类型匹配需求（IMAGE/VIDEO/STRING 等），再向用户展示
4. 用户跑成功 → `workflow verify <webappId>` + `workflow add <webappId> --task X --title ... --note ...` 入库

**入库规则**：只有确认可用的才 add；没实测过的标 `verified=false`（目录展示 `?`），跑成功一次后 verify 变 `✓`。目录为空时引导用户浏览市场（`--list --sort HOTTEST`），或用 `references/discover-bilibili.md` 从 B 站视频发现工作流。

## 错误处理

脚本 stderr 输出 JSON 含 `error` 字段与修复指引。视频 `TASK_FAILED` → 换模型重试（降级：全能V3.1 Fast → 可灵 → MiniMax H3）；`AUTH_FAILED` → 重新生成 key；`INSUFFICIENT_BALANCE` → 提示充值；`NO_NODES` → 应用需先在网页端跑过一次。

## 消费级 Key 路径（消耗 RH 币）

用户使用**消费级 API Key**（对应 RH 币）时，调用路径与标准模型 API 不同：走 `/task/openapi/*`（AI 应用 / ComfyUI 工作流），含 WebSocket 进度、上传链接、seed 重置等坑。**跑任何消费级路径的任务前，先读 `{baseDir}/references/rh-coin-path.md`** 并按其检查清单校验（seed 入 nodeInfoList、[] 连线不动、上传链接 1 天有效等）。该文档是自研知识沉淀，已实测验证。
