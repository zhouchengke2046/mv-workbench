# RH 工作流 API 全流程与诊断（原 SKILL.md ①-⑨ + 进阶参考）

> 前置速览见主 SKILL.md「全流程一览」。字段名、`api/` 前缀、错误码与诊断顺序不可自由发挥。

## ① 前置检查（三条，缺一不可）
```bash
# 1) 确认走哪把 key —— 环境变量会覆盖配置文件！
rh auth show                     # 若使用 rh CLI
#    ⚠️ RUNNINGHUB_API_KEY 由 mv_keys.py exec 注入；不要依赖其他配置来源
#    要用配置里的号：unset RUNNINGHUB_API_KEY

# 2) 余额（CLI 只显示钱包，RH币必须走 API）
POST /uc/openapi/accountStatus   {"apikey":"<key>","extension":"all"}
#  → remainCoins(RH币) / remainMoney(钱包¥) / currentTaskCounts(运行中)

# 3) 队列必须空闲，否则提交被 421 拒
#    currentTaskCounts == 0 再提交；并发为 1 的账号尤其容易撞满
```

## ② 上传素材 —— 全流程唯一的硬坑
```bash
POST https://www.runninghub.cn/task/openapi/upload
form-data: apiKey=<key>  fileType=input  file=@本地文件
→ {"code":0,"data":{"fileName":"api/<sha256>.mp4","fileType":"input"}}
```

**🔴 必须原样使用 `data.fileName`（含 `api/` 前缀）作为 fieldValue。**

| 做法 | 结果 |
|---|---|
| 原样用 `api/<sha256>.mp4` | ✅ 正常 |
| 去掉前缀用 `<sha256>.mp4` | ❌ **静默失败**：工作流读不到文件，主链整条不执行；任务 10~40s 秒回、状态仍 SUCCESS、只花 1~7 RH币、产物是无关小文件，**不报任何错** |

**由此得出最有用的判别表**：

| 指标 | 正常 ✅ | 静默失败 ❌ |
|---|---|---|
| 耗时 | 180~700s | **10~40s** |
| 消耗 | 36~235 RH币 | **1~7 RH币** |
| 产物 | mp4 + 附带文件 | 只有无关小文件 |
| 报错 | — | **无** |

**看到"秒回 + 消耗个位数 RH币 + 产物莫名其妙"，第一个动作就是查 fieldValue 有没有丢前缀。**

> 附带认知（省得误判）：
> - 上传后的文件名 = **文件内容的 SHA256**，内容寻址。**同一文件无论从 API 还是网页上传都得到同一个名字**——两端共享同一存储，不存在"API 上传不生效"。
> - 工作流节点里显示的默认值（如 `590e440f….mp4`）是**纯 hash**，那是 RH 内部存储形式；**自己提交时必须给 `api/<hash>` 全名**，别照默认值样式改。
> - 另有 v2 上传通道 `POST /openapi/v2/media/upload/binary`（Bearer 鉴权），返回 `fileName=openapi/<hash>` + 带签名 `download_url`；但 **v2 提交接口 `/openapi/v2/run/ai-app/<id>` 对部分应用返回 414，别默认它可用**。

## ③ 组装 nodeInfoList
```json
[{"nodeId":"137","fieldName":"image","fieldValue":"api/<sha256>.png"},
 {"nodeId":"165","fieldName":"video","fieldValue":"api/<sha256>.mp4"}]
```
- **只写需要改的节点**即可，其余走工作流默认值；也可传空数组跑默认值做对照。
- 该改哪些节点？三种取法见下方「诊断三件套」。
- ⚠️ 传了 `frame_load_cap` 这类会**截断**视频的节点，输出时长就随你传的值；**不传**则由工作流按时长自动算、输出时长 = 源时长（推荐，后续换音轨不会错位）。

## ④ 提交任务
```bash
POST https://www.runninghub.cn/task/openapi/create
{"apiKey":"<key>", "workflowId":"<id>", "nodeInfoList":[...], "instanceType":"default|plus"(可选)}
→ {"code":0,"data":{"taskId":"...","netWssUrl":"wss://...","taskStatus":"RUNNING"}}
```
- `workflowId` 对应网页 `/workflow/<id>`；**AI 应用**则是 `/task/openapi/ai-app/run` + `webappId`，两者不是一回事。
- 返回的 `netWssUrl` 是实时执行通道，排查时非常有用。

## ⑤⑥ 轮询与取产物
```bash
POST /task/openapi/status   {"apiKey":"<key>","taskId":"<id>"}  → data: "RUNNING"|"SUCCESS"|"FAILED"
POST /task/openapi/outputs  {"apiKey":"<key>","taskId":"<id>"}  → data: [{fileUrl,fileType,nodeId,consumeCoins,taskCostTime}]
```
**FAILED、或"成功却没产物"时，必须拉 `outputs` 的 `failedReason`**（含 `traceback` / `node_name` / `node_id` / `exception_message`）。**只看 status 只能得到 FAILED 三个字母，查不出任何原因。**

## ⑦ 诊断三件套

**A. 读工作流完整结构**（最有用，动手前先做）
```bash
POST /api/openapi/getJsonApiFormat    {"apiKey":"<key>","workflowId":"<id>"}
→ data.prompt = 完整 ComfyUI 图 JSON（**是字符串，需二次 json.loads**）
   结构 {"<nodeId>":{"class_type":"...","inputs":{...}}, ...}，含全部节点/参数/连线
```
看清三件事：① 生成链是否存在 ② 哪些是输入口 ③ 各输入的默认值格式。

**B. WebSocket 实时执行链**（判断"哪个节点没被调度"）
```
直连 create 返回的 netWssUrl，事件序列：
status → execution_start → execution_cached → executing(node) → progress(value,max) → executed(node,output) → execution_success
```
- `execution_cached.nodes` 列出被缓存跳过的节点
- **若某节点从未出现在 `executing` 里，说明它根本没进入执行计划**（而非执行失败）
- `progress.max` 可验证传入参数是否真的生效

**C. 错误差异法探节点**（无需文档，零成本）
故意传一个**不存在的 fieldName**，按返回 reason 判断：
| reason | 含义 |
|---|---|
| `field_not_found_in_node_inputs` | **节点存在** |
| `node_not_found_in_workflow` | 节点不存在 |

> ⚠️ 只有"不存在的字段名"免费；传真实字段名会**直接创建任务并扣费**。

## ⑧ 错误码对照
| 码 | 含义 | 处置 |
|---|---|---|
| 421 | `TASK_QUEUE_MAXED` | 队列满，等 `currentTaskCounts` 归零再提 |
| 414 | `TASK_CREATE_FAILED_BY_NOT_ENOUGH_POWER_VALUE` | 余额低于阈值，换号或充值 |
| 803 | `NODE_INFO_MISMATCH(...)` | 节点/字段对不上；也可当探节点手段 |
| 901 | `webapp not exists` | 该 ID 不是可调用的 AI 应用 |
| 809 | `APIKEY_FILE_SIZE_EXCEEDED` | 文件过大 |
| 1602 | `HEADER_API_KEY_NOT_FOUND` | 该端点要 Bearer 头，不是 body 里的 apiKey |

## ⑨ 排查心法（血泪教训）
1. **先用一个已知稳定的工作流验证基础链路**（能不能传参、能不能出片），再碰复杂工作流。
2. **优先读现成实现**——已有跑通的代码直接对照，比从零猜快得多。
3. **别从单次失败下结论**。曾据一次堆栈推断"平台审核拦截真人照片"，被对照实验推翻。
4. **对照实验一次只改一个变量**，且必须包含一个"已知会成功"的对照组。

---


## 进阶参考

### AI 应用 vs 工作流：两条独立通道
| 实体 | 网页 URL | 运行接口 | 参数 |
|---|---|---|---|
| **AI 应用**（webapp） | `/ai-detail/<id>` | `POST /task/openapi/ai-app/run` | `webappId` + `nodeInfoList` |
| **工作流**（workflow） | `/workflow/<id>` | `POST /task/openapi/create` | `workflowId` + `nodeInfoList` |

两者的状态/产物查询共用 `/task/openapi/status`、`/task/openapi/outputs`。

**AI 应用的官方调用示例**可以直接读出来（`rh app run` 走的就这个端点）：
```bash
GET /api/webapp/apiCallDemo?apiKey=<key>&webappId=<id>
# data 里的字段：
#   curl           → 官方完整调用示例（端点+body+全部节点+description）★权威格式，先读它
#   nodeInfoList[] → 每个 {nodeId, fieldName, fieldValue, description}
#   webappName     → 应用真名（能判断用的什么模型）
#   description / covers / tags / accessEncrypted
```
**AI 应用与工作流的差别**：AI 应用要求**全部节点都提交、每项都带 `description`**；工作流只传要改的节点即可。

#### ⚠️ 走错端点的两个典型报错（2026-09-19 实测）
| 现象 | 原因 | 正确做法 |
|---|---|---|
| `{"code":380,"msg":"workflow not exists"}` | **拿 webappId 去调 `/task/openapi/create` + `workflowId`**。工作流市场 `aiapp/list` 抓到的全部是 AI 应用 ID，不是 workflowId | 改调 `POST /openapi/v2/run/ai-app/<webappId>` |
| `v2` 端点报 414 | 该应用不支持 v2 通道（**并非全都不支持**） | 换 `rh app run <id>`（CLI 走 v1）|

v2 调用骨架（**已跑通 16/16**，案例：音色迁移 `2066748890128412673`）：
```bash
POST https://www.runninghub.cn/openapi/v2/run/ai-app/<webappId>
Authorization: Bearer <key>
{"nodeInfoList":[{"nodeId":"2","fieldName":"audio","fieldValue":"api/<hash>.wav","description":"..."}],
 "instanceType":"default","usePersonalQueue":"false"}
```
🔴 **该端点直接返回任务对象，没有 `code` 包裹**：`{"taskId":"2101...","status":"RUNNING","clientId":"...","failedReason":{}}`。
按 `if resp["code"] != 0` 判失败会**把成功当成失败**（错误信息里能看到 taskId 却以为没提交，重复提交白扣币）。
正确取法：`taskId = resp.get("taskId") or resp["data"]["taskId"]`。

**音色迁移/变声类应用产物**：输出常见为 **22.05kHz mono FLAC**，回贴进视频前需重采样（`-ar 24000 -ac 1`）。

### 批量枚举工作流节点（省去逐个试）
遍历 nodeId（实测 1~1200、16 并发、42 秒跑完）用错误差异法筛出可编辑节点，某 H3 工作流一次挖出 **58 个**。
> 配合 `getJsonApiFormat` 使用更完整：枚举给「有哪些节点」，`getJsonApiFormat` 给「每个节点是什么、怎么连」。

`getJsonApiFormat` 的一个小坑：**别用 `'"nodes"' in text` 判断是否拿到图**——该结构的 key 是 nodeId，没有 `nodes` 字样，会误判成失败。正确判断是看 `data.prompt` 是否存在。

### WebSocket 实时通道补充
- `executed` 事件里的 `output` 就是该节点产物（图像/文本/视频），**比 `/task/openapi/outputs` 覆盖更全**（后者只返回挂了保存节点的产物）
- 连接凭据 `Rh-Comfy-Auth` 已含在 `netWssUrl` 里，直接连即可；任务结束连接自动断开
- 节点顺序无意义，关键看**哪些节点从未出现**

## 控制生成时长（视频类工作流通用，节点是 `VHS_LoadVideo`）


用户最常踩的"爆显存"就是这里：
- **生成秒数 = `frame_load_cap` ÷ `force_rate`**（H3 等模型原生 24fps）
- `frame_load_cap` 默认值可能是 `0`（**不限制，最危险**）或作者写死的 `360`（= 15s，已是 H3 上限）
- 要限时长：设 `frame_load_cap = 目标秒数 × 24`（10s → 240，5s → 120，3s → 72）
- 想再省显存：`select_every_nth=2` 让帧数减半（代价是动作精细度下降）
- `skip_first_frames` 可跳过片头无用帧；`force_rate` 一般保持 24

