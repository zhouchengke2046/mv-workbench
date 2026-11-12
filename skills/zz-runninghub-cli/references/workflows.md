# RunningHub 工作流总表

> 机器可读真源：`references/workflows.json`（Updated 2026-11-03）
> 本文件由 `python3 scripts/rh_registry.py render` 生成，**勿手改**。
> 默认：consumer key，3 并发。消费级 key，扣 RH 币；共享/企业 key 未经用户明确允许不得使用。

## 怎么用

```bash
python3 scripts/rh_registry.py route "我要做的事"   # 不知道选哪个：先问它
python3 scripts/rh_registry.py show <ID|别名>       # 看参数/成本/坑
python3 scripts/rh_registry.py find <关键词>        # 搜全表
python3 scripts/rh_registry.py list --all           # 全部登记项
```

## 30 秒路由

| 我要… | 工作流 | 说明 |
|---|---|---|
| 漫剧/课文短片出视频（默认） | `2110943749894402050` YZ金鱼-MiniMax H3 终极篇-文武双全 | 先读 h3-prompt-writing/SKILL.md |
| 更高质量/电影感/听说了吗 | `2101142038568849410` 宏雷HyLan-MiniMax H3 双采样 V3 | 慢但电影感最好；枚举字段必须显式覆盖 |
| 有首帧，图生视频 | `2104168698222301186` H3 I2VA 单首帧 | length 传帧数（24fps），不是秒 |
| 出资产图/角色定妆/场景道具 | `2116462203997081601` MOSS 文生图 | 先读 zz-manju-image-prompts/SKILL.md |
| 批量换人/人物替换 | `2099805997966643202` 人物替换单人稳定版｜MiniMax H3 | 先读 references/batch-replace.md；上传必须保留 api/ 前缀 |
| 跨段音色统一/音色漂移 | `2066748890128412673` 音色迁移 VC（AI 应用） | 听说了吗固定后处理；配合 F0 审计 |
| 声音克隆/配音备选 | `2073652333510217729` YZ金鱼-IndexTTS 2 超自然语音克隆 | 默认先用 mimo-tts；RH 这条是备选 |
| Qwen3 TTS 旁白（备选） | `2086427153989726210` RunningHub Qwen3 TTS | 2–11 币/次；edge-tts/MiMo 之外的备选 |
| 720P→1080P/超分 | `2099761219182882817` Topaz 超分（AI 应用） | 1080P 直出会 OOM，先 720P 再超分 |
| 找新工作流/扫榜 | — | 跑 scripts/scan_apps.py；命中后先 apiCallDemo 探节点，再登记到 workflows.json |
| 查余额/任务失败/没产物 | — | 先读 references/api-flow.md 的排障三件套；用 accountStatus 查余额 |
| 写 H3 提示词 | — | 不是 RH 任务：用 h3-prompt-writing（规范）+ zz-manju-prompt（翻译/机检） |
| 打斗/高动态候选 | — | 见 references/workflows.md 的“只收藏未接入”段；需网页保存换取 workflowId |

## 主线

| ID | 名称 | 域/形态 | 成本 | 用在 | 注意 |
|---|---|---|---|---|---|
| `2110943749894402050` | YZ金鱼-MiniMax H3 终极篇-文武双全 | H3 视频/workflow | 12 + 4.05 × MP × 秒（RH币） | mv-workbench；一觉醒来宠物店；一觉醒来大学生；卖油翁；曹冲称象 | 显式清空未用槽位；0.41MP 只用于试错，正式成片升 0.92MP+ |
| `2101142038568849410` | 宏雷HyLan-MiniMax H3 双采样 V3 | H3 视频/workflow | 6s@720P 约 38 RH币（2026-09-30 实测） | tingshuole-video；结算日v3；刻舟求剑 A/B | 枚举字段必须显式覆盖英文值，网页保存态可能是中文标签；steps=6 时 H3SigmaRefiner 静默失效 |
| `2104168698222301186` | H3 I2VA 单首帧 | H3 视频/workflow | 10s 约 136 RH币（2026-10-15 实测，约 13–14 币/秒） | 礼仪大师；结算日；xiaomi-apple-ad；apple-ad-style | length 传帧不是秒；5→0.2s 事故；失败/超时仍可能计费 |
| `2116462203997081601` | MOSS 文生图 | 图片/资产图/workflow | 2026-11-03 实测 default(24G) 0.41MP≈24、2MP≈28–49 RH/张；plus(48G) 同图 0.41MP=32（约+33%）；旧 3–12 为活动价 | mv-workbench；一觉醒来宠物店；一觉醒来大学生；曹冲称象 | 消费级 key，并发以账号实际为准；显式传 instanceType=default；plus 约贵 33% |
| `2099805997966643202` | 人物替换单人稳定版｜MiniMax H3 | 视频换人/workflow | 36–50 RH币/段（单段 370–680s） | zz-runninghub-cli/references/batch-replace.md | 上传文件名必须带 api/ 前缀，否则 10–40s 秒退 SUCCESS 但产物错；H3 会重编语音和画面文字，必须换回原音轨/裁字 |
| `2066748890128412673` | 音色迁移 VC（AI 应用） | 音色迁移/ai-app |  | tingshuole-video | 生成侧锁不住音色，后期 VC + F0 审计是固定流程 |

## 备用

| ID | 名称 | 域/形态 | 成本 | 用在 | 注意 |
|---|---|---|---|---|---|
| `2084675422083702785` | H3 全能参考加速版 v4（AI 应用） | H3 视频/ai-app |  | tingshuole-video；灵兽AI | 当前停用：服务端 RHLLMChatNode 报 LLM API balance insufficient；该余额独立于 RH 币；失败任务也扣币 |
| `2092446042583642113` | MiniMax H3 真实电影质感 | H3 视频/workflow | plus 档 |  |  |
| `2100206317607673858` | H3-I2VA | H3 视频/workflow |  | EP006 |  |
| `2108916432099700738` | H3 无损融合单采 | H3 视频/workflow | plus 1080P 档 | 刻舟求剑 A/B | A/B 对照：双采样 V3 与无损单采各跑一段再选 |
| `2090316739765686274` | MiniMax H3 文生视频（AI 应用） | H3 视频/ai-app | 5s 约 48–57 RH币 | panxiaobao-mix | 无参考图依赖，适合纯文生；5s 片段约 160–290s 正常 |
| `2100760443840188417` | minimaxH3 单采双采工作流｜文生视频图生视频 | H3 视频/ai-app |  |  | 分辨率不可控，不放正式产线 |
| `2114532396111589377` | MOSS 审核回退（现金/钞票场景） | 图片/资产图/workflow |  | mv-workbench | 只作为审核回退，默认不改主力；参数与形态未在本 skill 完整验证 |
| `2073652333510217729` | YZ金鱼-IndexTTS 2 超自然语音克隆 | TTS/声音克隆/ai-app |  | mv-workbench | 上传参考音保留 api/ 前缀；默认不启用，先跑 MiMo smoke |
| `1965614643077070850` | 声音克隆 IndexTTS2 史上最强音色克隆带语气 | TTS/声音克隆/ai-app | 约 12 RH币/次，均 49s | 团姐音色测试 | 12/15/17/37/38/39 都接受 audio，但只有 13 是参考音入口；填错 SaveAudio 会 TypeError；音频用 WAV 44.1k mono 16bit 最稳 |
| `2099761219182882817` | Topaz 超分（AI 应用） | 超分/后期/ai-app | 约 1/4 的 1080P 直出成本 | H3 产线 | 1080P 直出会 OOM；先 720P 再超分 |

## 候选 / 未测

| ID | 名称 | 域/形态 | 成本 | 用在 | 注意 |
|---|---|---|---|---|---|
| `2085304953094107137` | 加速版-MiniMax H3｜多参图像音频生视频 | H3 视频/ai-app |  |  | 未实测；先用 apiCallDemo 探节点 |
| `2080366767460929538` | LTX2.3 角色一致性 | H3 视频/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080554402154377217` | LTX2.3 图生视频 | H3 视频/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2079739260529369089` | Wan2.2 Remix | H3 视频/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2066366778678272001` | Flux2-Klein-9B（画质主力） | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080868158872834050` | Krea2 双图编辑·角色一致性（图生图） | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080845945562030081` | Krea2 超写实 | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080900950625185794` | 光影氛围 | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080849606778376194` | Z-Image-1 加速 | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2079737939252305921` | Z-Image 8K | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2080486881292283905` | Z-Image 4K 人像 | 图片/资产图/unknown |  | fanren-juchang-producer | 先 apiCallDemo 确认形态与节点 |
| `2086427153989726210` | RunningHub Qwen3 TTS | TTS/声音克隆/workflow | 2–11 RH币/次（约 0.4–0.6 币/字） | 旁白配音选型 | 整篇 58 句约 200 币，比一段 H3 视频便宜 |
| `2100233892983828481` | 坤坤 MiniMax H3 多参单采 8 步加速 | H3 视频/ai-app |  |  | 未测，先用 apiCallDemo 探节点 |

## 停用

| ID | 名称 | 域/形态 | 成本 | 用在 | 注意 |
|---|---|---|---|---|---|
| `2086426527046135809` | MiniMax H3 参考视频 | H3 视频/workflow | plus 档 | 早期对比 | 实测 SUCCESS 但 outputs 全空；不要用于正式产线 |
| `2101003521838632962` | MiniMax H3 单采双采视频生成处理（已废） | H3 视频/ai-app |  | 旧 AI开头02 | 不要再用；新工程从 2090316739765686274 复制 |

## 只收藏未接入（帖子，不是 workflowId）

| 帖子 | 名称 | 域 | 说明 |
|---|---|---|---|
| `post/2078339206589542401` | Krea2 巨构（RH 帖子） | 图片/资产图 | megastructure-prompt 常用的 Krea2 巨构工作流帖子；未转成自己的 workflowId。 |
| `post/2095430950619537409` | AI代码侠土豆 · H3 打斗-双采 | H3 视频 | 收藏候选；打斗专用 + 打斗 Skill。 |
| `post/2095430334602113026` | AI代码侠土豆 · H3 打斗-单采 | H3 视频 | 收藏候选；土豆打斗轻量版。 |
| `post/2094782408347447298` | Dasiwa 动态最强 参考生-双采 V1 | H3 视频 | 收藏候选；武侠打斗 + 游戏级特效。 |
| `post/2095105300293574657` | Dasiwa 动态最强 参考生-单采 | H3 视频 | 收藏候选；Dasiwa 参考生轻量版。 |
| `post/2094749351989043201` | Dasiwa 动态最强 文生-双采 | H3 视频 | 收藏候选；Dasiwa 文生双采。 |
| `post/2094938114493083650` | Dasiwa 动态最强 文生-单采 | H3 视频 | 收藏候选；Dasiwa 文生单采。 |
| `post/2094673232666742786` | 全能工作流（双采+残影修复+双重去油+远景优化+DLSS5） | H3 视频 | 收藏候选；治加速 LoRA 油腻/塑胶感/远景面部糊。 |
| `post/2100146680422281217` | MiniMax H3｜8步武术动作控制 | H3 视频 | 收藏候选；动作控制向。 |
| `post/2098815909289177089` | 全能生视频 V4（单采 2K 直出） | H3 视频 | 收藏候选；文/图/参考三合一 + 官方 skill 提示词优化，2K 直出。 |
| `post/2086597344037384194` | TE-int8 二采极速版 | H3 视频 | 收藏候选；文生/图生/全能参考 + 旁路修复，速度向。 |

> 这些只有 RH 帖子 ID，必须先在自己的账号里打开并保存一次，才能拿到可 API 调用的 workflowId。

## 维护规则

1. 新增/改状态只改 `references/workflows.json`，再跑 `python3 scripts/rh_registry.py render`。
2. 项目文档可以写“本项目固定用哪个 ID”，但不要另建一份总表；总表以本文件为准。
3. 状态变化：跑通一次才从 `candidate` 升 `main`/`backup`；实测有问题降 `deprecated` 并写清原因。
4. 帖子候选只有换成 workflowId 后，才登记 `id` 并补 `endpoint`/`params`。
