---
name: zz-runninghub-cli
description: RunningHub（RH）总入口与操作层。先用它决定“该用哪个工作流/哪个 skill”：漫剧/课文短片 H3 视频、资产图 MOSS、批量换人、TTS/声音克隆、音色迁移、Topaz 超分、扫榜找新工作流、查余额、调 API、排障。含工作流 API 全流程（上传→nodeInfoList→create→status→outputs→下载）、api/ 前缀坑、错误码、AI 应用 vs workflow 区分、消费级/共享 key 计费。当用户说“用 RH 跑”“该用哪个工作流”“批量换人”“RH 余额/任务失败/没产物”“找个能做 X 的工作流”时调用。
agent_created: true
---

# RunningHub 总入口（zz-runninghub-cli）

> **唯一入口**。工作流唯一真源 = `references/workflows.json`；人读视图 = `references/workflows.md`（由脚本生成，勿手改）。
> 不知道用哪个：先跑 `python3 scripts/rh_registry.py route "我要做的事"`。

## 0. 30 秒路由

| 我要… | 默认 | 形态 | 下一步 |
|---|---|---|---|
| 漫剧/课文短片出视频（默认） | `2110943749894402050` YZ金鱼-终极篇-文武双全 | workflow | 读 `h3-prompt-writing/SKILL.md` |
| 更高质量/电影感/听说了吗 | `2101142038568849410` 双采样 V3 | workflow | 读 `h3-prompt-writing/SKILL.md` |
| 有首帧，图生视频 | `2104168698222301186` H3 I2VA 单首帧 | workflow | `length` 传帧数（24fps），不是秒 |
| 出资产图/角色定妆/场景道具 | `2116462203997081601` MOSS 文生图 | workflow | 读 `zz-manju-image-prompts/SKILL.md` |
| 批量换人/人物替换 | `2099805997966643202` 人物替换单人稳定版 | workflow | 读 `references/batch-replace.md`；上传保留 `api/` 前缀 |
| 跨段音色统一/音色漂移 | `2066748890128412673` 音色迁移 VC | AI 应用 | `tingshuole-video/templates/fix_voice.py` |
| 声音克隆/配音备选 | `2073652333510217729` YZ金鱼-IndexTTS 2 | AI 应用 | 默认先用 `mimo-tts`，RH 这条是备选 |
| Qwen3 TTS 旁白（备选） | `2086427153989726210` Qwen3 TTS | workflow | 2–11 币/次；edge-tts/MiMo 之外的备选 |
| 720P→1080P/超分 | `2099761219182882817` Topaz 超分 | AI 应用 | 1080P 直出会 OOM，先 720P 再超分 |
| 找新工作流/扫榜 | — | — | 跑 `scripts/scan_apps.py`；命中后先 `apiCallDemo` 探节点，再登记 |
| 查余额/任务失败/没产物 | — | — | 先读 `references/api-flow.md` 的排障三件套 |
| 写 H3 提示词 | — | — | 不是 RH 任务：`h3-prompt-writing`（规范）+ `zz-manju-prompt`（翻译/机检） |
| 打斗/高动态候选 | — | — | 见 `references/workflows.md` 的“只收藏未接入”段；需网页保存换取 workflowId |

> 全表（含备用/候选/停用/只收藏帖子）：`references/workflows.md`。查详情：`python3 scripts/rh_registry.py show <ID|别名>`。

## 1. 相关 skill 分工（别重复找）

| Skill | 什么时候用 | 和本 skill 的边界 |
|---|---|---|
| `h3-prompt-writing` | 写 H3 提示词（官方 T2VA/I2VA/FL2VA/Ref2VA 规范） | 只写提示词，不提交任务 |
| `zz-manju-prompt` | 漫剧提示词翻译 + 机检（只查语法/引用/禁词） | 不决定工作流；路由回本 skill |
| `mv-workbench` | 漫剧工作台、全流程导航、资产/视频默认产线 | 固定 MOSS/H3 默认；执行仍走本 skill 的 API |
| `tingshuole-video` | 「听说了吗」项目全流程（分镜台、剪辑、音色、包装） | 项目专用；分镜台只内置 v3/v4 两条 |
| `panxiaobao-mix` | 盘小宝 AI 开头混剪 | 用 H3 文生 AI 应用 `2090316739765686274` |
| `apple-ad-style` | 苹果风广告（已冻结） | 只保留 `2104168698222301186` 的成本基准 |
| `zz-asset` | 资产设定与出图边界 | 不执行生成；出图交本 skill |

## 2. 核心方法：调用 RH 工作流全流程

> CLI 的 `rh app run` 内部走的也是这套 API；需要精确控制、批量或排障时直接调 API。

```
① 前置检查   鉴权（哪把 key）+ 余额 + 队列空闲
② 上传素材   POST /task/openapi/upload      → api/<sha256>.<ext>
③ 组装入参   只写要改的节点
④ 提交任务   POST /task/openapi/create      → taskId
⑤ 轮询状态   POST /task/openapi/status      → RUNNING / SUCCESS / FAILED
⑥ 取产物     POST /task/openapi/outputs     → [{fileUrl, fileType, nodeId, consumeCoins}]
⑦ 下载       GET fileUrl
```

- **workflow**：`POST /task/openapi/create` + `workflowId` + `nodeInfoList`
- **AI 应用**：`POST /task/openapi/ai-app/run` 或 `/openapi/v2/run/ai-app/<webappId>` + `nodeInfoList`
- 两者不是一回事：拿 AI 应用的 webappId 去调 `create` 会报 `WORKFLOW_NOT_EXISTS`。
- 完整七步、`api/` 前缀坑、诊断三件套、错误码、WebSocket、时长控制：`references/api-flow.md`。

## 3. 账号与 key

- 通过 `mvwb keys set runninghub`（或 `mv_keys.py set runninghub`）配置；生成时由 `mvwb`/`mv_keys.py exec` 注入 `RUNNINGHUB_API_KEY`。
- 消费级 key 扣 RH 币；企业共享 key 扣钱包 ¥，并发更高；**未经账号所有者允许不要用共享 key**。
- 消费级 key 默认约 1 并发；批量前先确认账号并发和余额。
- 查完整余额（RH 币 + 钱包 + 队列）：
  ```bash
  curl -s -X POST https://www.runninghub.cn/uc/openapi/accountStatus \
    -H "Content-Type: application/json" \
    -d '{"apikey":"<KEY>","extension":"all"}'
  ```
- 不要依赖 shell 里残留的 `RUNNINGHUB_API_KEY`；统一用 `mvwb`/`mv_keys.py exec` 读取 `~/.config/mv-workbench/keys.json`。
- 失败/超时任务仍可能扣费；批量前先报「段数 × 单价 ≈ 总币」。

## 4. CLI / 脚本入口

```bash
# 有 rh CLI 时
rh check                     # 连通 + 钱包余额（不含 RH 币）
rh auth show                 # 当前 key
rh app list --sort HOTTEST   # 工作流市场（不支持关键词搜索）
rh app info <webappId>       # 读可改节点
rh app run <webappId> --node <nodeId>:<fieldName>=<值>

# 本机没有 rh 时（当前 Mac 就是这种情况）
python3 ~/github/runninghub-upstream/runninghub/scripts/runninghub.py --help
python3 ~/github/runninghub-upstream/runninghub/scripts/runninghub_app.py --list
```

项目内可直接复用的参考实现：

| 脚本 | 用途 |
|---|---|
| `mv-workbench` 项目的 `moss_gen.py` / `h3_gen.py` | MOSS 出图 / 终极篇 H3 跑批 |
| `tingshuole-video/templates/分镜台.py` | 听说了吗分镜台（内置 v3/v4） |
| `一觉醒来宠物店/coding/h3_gen.py`、`moss_gen.py` | 0.41MP H3 / MOSS 批量 |
| `礼仪大师/tools/rh.py`、`结算日/tools/rh.py` | H3 I2VA 单首帧批量 |
| `panxiaobao-mix` 的 `rh_h3.py` | H3 文生 AI 应用（盘小宝） |

> 新项目优先复制上面的脚本，不要从零写一套；提交前把 `workflowId` 对齐 `references/workflows.json`。

## 5. 已知坑 Top

1. **上传文件名必须保留 `api/` 前缀**。去掉后工作流读不到文件、主链不执行，任务 10–40 秒“秒退”但状态 SUCCESS、只花 1–7 币、产物是无关小文件，且不报错。
2. **`length` 是帧不是秒**：H3 I2VA 工作流按 24fps 计，96–360 帧 = 4–15s；把 5 当秒会出 0.2s。
3. **枚举字段必须显式覆盖英文值**：网页保存态可能存的是中文 UI 标签（`参考生视频`/`按序号`/`English`），API 只认 `reference`/`index`/`en`；漏覆盖会 `805 prompt_outputs_failed_validation`（提交前校验，不扣币）。
4. **AI 应用 vs workflow 先确认**：详情页 `/ai-detail/<id>` 是 AI 应用，`/workflow/<id>` 是 workflow；调错端点会 901/803。
5. **`2086426527046135809` 是预览型输出**：实测 SUCCESS 但 outputs 全空；不要用于正式产线。
6. **1080P 直出会 OOM 且失败照样扣币**：先 720P 生成，再 `2099761219182882817` Topaz 超分。
7. **421 排队 / 817 不可取消**：421 按日志重试，不重复建任务；817 等结束，不要反复提交。
8. **H3 对“静态预期”会输出全静止**：要动必须在提示词里写显式连续动作。
9. **H3 会自己编画面文字和语音**：换人/参考视频路线必须换回原始音轨，字幕区域裁掉或重压。

## 6. 工作流搜索 / 发现

- `rh app list` 不支持关键词过滤；站内搜索接口全部不可用。
- 替代方案：`POST /openapi/v2/aiapp/list` 分页抓榜单 + 本地关键词过滤（`scripts/scan_apps.py`，约 1 分钟抓 4000 条）。
- 榜单记录的 `webappId` 要从 `invokeExample` 正则提取；`records` 里没有该字段。
- 找到新工作流后：网页打开 → 保存 → `apiCallDemo` 探节点 → 跑通一次 → 登记到 `references/workflows.json` → `render`。

## 7. 维护规则

0. **工作流真源是 `references/workflows.json`**；改完跑 `python3 scripts/rh_registry.py render` 生成 `workflows.md`，不要手改生成文件。
1. **新增/改状态只改 `references/workflows.json`**，再跑 `python3 scripts/rh_registry.py render` 生成 `workflows.md`。
2. 项目文档可以写“本项目固定用哪个 ID”，但不要另建总表；总表以 `workflows.json` 为准。
3. 跑通一次才从 `candidate` 升 `main`/`backup`；实测有问题降 `deprecated` 并写清原因。
4. 帖子候选只有换成 workflowId 后，才登记 `id` 并补 `endpoint`/`params`。
5. 批量换人已从独立 skill 并入 `references/batch-replace.md`；不要再找 `rh-batch-video-replace`。

## 8. 参考

- `references/workflows.json` / `references/workflows.md` — 工作流总表（唯一真源 / 生成视图）
- `references/api-flow.md` — API 七步、错误码、诊断
- `references/batch-replace.md` — 批量换人完整 recipe
- `references/rh-coin-path.md` — 消费级 key 扣币路径
- `references/rhcli-adapter.md` — 薄适配层/自进化记忆
- `references/discover-bilibili.md` — B 站工作流发现
- `scripts/rh_registry.py` — `route/list/show/find/render/validate`
- `scripts/scan_apps.py` — 扫榜 + 本地关键词过滤
