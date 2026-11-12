# RH 币路径（消费级 API Key）— 知识沉淀

> 来源：RunningHub 官方 API 文档 + 消费级 key 实测（2026-09）。本文件是 zz-rhcli 自研知识，与上游 skill 无关。

## 背景：RunningHub 两条调用路径

| | 企业级共享 API Key（消耗钱包余额） | 消费级 API Key（消耗 RH 币） |
|---|---|---|
| 接口根 | `/openapi/v2/*`（Bearer 认证） | `/task/openapi/*`（apiKey 在 body/表单/query + 部分带 Bearer 头） |
| 能力 | 标准模型 API（420+ 端点）、LLM API | AI 应用、ComfyUI 工作流、上传资源 |
| 调用范式 | 提交 → 轮询 → 下载（`runninghub.py` 已覆盖） | 提交 → **WebSocket 进度**或轮询 → 下载（复杂度高） |
| 计费 | 钱包余额 | RH 币 |

**模型 API 和 LLM API 仅支持企业级 key；消费级 key 的主战场是 AI 应用 + ComfyUI 工作流。**

## 消费级路径完整端点表

| 端点 | 方法 | 用途 | 认证方式 |
|---|---|---|---|
| `/task/openapi/ai-app/run` | POST | 运行 AI 应用（webappId + nodeInfoList） | body `apiKey` + Bearer 头 |
| `/task/openapi/create` | POST | ComfyUI 工作流高级（workflowId 或 workflow JSON 直传） | body `apiKey` + Bearer 头 |
| `/task/openapi/upload` | POST | 上传资源（form: apiKey/fileType/file），返回 `fileName` 回填 LoadImage 节点 | form 字段 |
| `/api/webapp/apiCallDemo` | GET | 查 AI 应用可修改节点（query: apiKey + webappId） | query 参数 |
| `/openapi/v2/aiapp/list` | POST | 应用市场浏览（current/size/sort=RECOMMEND\|HOTTEST\|NEWEST，HOTTEST 带 days） | Authorization 头 |
| 查询任务状态 / 查询任务生成结果 / 获取 Lora 上传链接 | — | 状态、结果、LoRA 三步链第一步 | — |

**必须带 `Host: www.runninghub.cn` 头**（部分接口校验域名）。

## 请求体（ai-app/run 与 create 通用字段）

```json
{
  "apiKey": "your-key",
  "webappId": 123,            // ai-app/run 用
  "workflowId": "456",        // create 用（或直接传 workflow 完整 JSON）
  "nodeInfoList": [{"nodeId": "6", "fieldName": "text", "fieldValue": "1 girl"}],
  "webhookUrl": "https://...",   // 可选：完成后回调
  "instanceType": "default"      // 可选：default=24G / plus=48G
}
```

## 响应中的关键字段

- `taskId` — 任务 ID
- `taskStatus` — `CREATE / SUCCESS / FAILED / RUNNING / QUEUED`
- `netWssUrl` — **WebSocket 实时进度地址**（含 `Rh-Comfy-Auth` 签名），断线用 `clientId` 重连
- `clientId` — 客户端 ID，页面刷新重连或二次运行需传
- `promptTips` — 工作流校验结果，`node_errors` 非空即节点配置错误

## Webhook 回调格式（webhookUrl 收到）

```json
{"event": "TASK_END", "taskId": "...", "eventData": "{\"code\":0,\"msg\":\"success\",\"data\":[{\"fileUrl\":\"...\",\"fileType\":\"png\",\"nodeId\":\"9\"}]}"}
```

## 硬性坑点（调用前必须检查）

1. **seed 被强制重置**：要固定随机种子，必须把 seed 写进 `nodeInfoList`。
2. **`fieldValue` 为 `[]` 包裹**：代表节点连线，禁止修改。
3. **纯前端逻辑字段在 API 不可用**：如 `control_after_generate`、`group` 相关——API 工作流 JSON 里找不到的字段就别传。
4. **AI 应用调用结果不携带工作流信息**：只有文件 URL。
5. **应用需先在网页端成功运行过一次**，否则查节点报 `NO_NODES`、运行可能失败。
6. **上传链接有效期 1 天**：批量/长任务不要复用旧 fileName。
7. **错误码速查**：`805` 工作流 ID 错误或权限不足；`814` 个人队列超限（独占 key 排队上限 1000）；`NO_NODES` 未跑过；`NODE_ERRORS` 节点校验失败。

## 两张图上传方案

- 方案 A（推荐简单）：**自维护图床 URL**，工作流用 `LoadImageFromUrl` 节点，`fieldValue` 直接填图片 URL。
- 方案 B：**上传资源接口** → 拿 `fileName` → 填进 `LoadImage` 节点 `fieldValue`。

## LoRA 上传三步链

1. 获取 LoRA 上传链接接口（拿预签名 URL）
2. 直传文件到该 URL
3. 在 `RHLoraLoader` 节点使用

## 实测记录（消费级 key，免费接口）

- `aiapp/list`：✅ 市场共 73382 个应用，推荐/最热/最新分页正常
- `webapp/apiCallDemo`：✅ 命中已在网页跑过的应用可返回 19 个可修改节点（BOOLEAN/SWITCH/STRING 等类型齐全）
- 企业级专有参数 `retainSeconds` / `usePersonalQueue` 对消费级 key **不生效**，无需处理
- `aiapp/list` 的 `title` / `keyword` 参数**均被忽略**（实测返回相同结果）→ **平台无关键词搜索 API**，只有 RECOMMEND / HOTTEST / NEWEST 三种排序

## 工作流发现（核心痛点与对策）

**痛点**：人人可发布 → 7 万+ 应用 → 不开网页几乎不可能"找到合适能用的"；平台又无搜索 API。

**对策 = 自建工作流目录（curated registry）**，存放于 `~/.runninghub/profile.json` 的 `workflows` 域（跨 Agent 共享）：

```json
"workflows": {
  "motion-transfer": [
    {"webappId": "1975951975441412098", "title": "Animate动作迁移V9",
     "note": "平台热榜，19个可调节点", "inputs": ["image","video"],
     "cost": "med", "verified": true}
  ]
}
```

**飞轮规则**（由 SKILL.md 的『工作流目录』一节驱动，agent 照做）：
0. **外部来源**：B站 UP 主视频（简介/置顶评论常带链接）→ 用 `zz-rh-discover` skill 的 `rh_bili.py <视频URL>` 提取 runninghub 链接
1. 先搜自建目录（`rh_profile.py workflow search X`）→ 命中直接给 webappId
2. 未命中 → `runninghub_app.py --list` 按 HOTTEST/NEWEST 浏览，人工筛标题/描述
3. `--info <webappId>` 确认输入类型匹配（IMAGE/VIDEO/STRING/SWITCH）
4. 跑成功后 `workflow verify` + `workflow add` 入库 → 目录越来越准，最终不再需要开网页

**入库纪律**：未实测的 `verified=false`（显示 `?`）；只有跑成功一次才标 `✓`；禁止用未验证的 webappId 直接跑任务。

## 与 zz-rhcli 的衔接

- `runninghub_app.py` 覆盖：浏览 / 查节点 / 上传 / 运行 / HTTP 轮询
- `rh_sdk.py`（SDK 封装）已补齐：**取消任务**、**查工作流JSON**、**LoRA上传三步链**、**workflow JSON直传**、账户详情、队列状态、结果下载、复制工作流
- 原生 ComfyUI 代理：`/proxy/<apiKey>` = 24G 机器、`/proxy-plus/<apiKey>` = 48G 机器 —— 等同 `http://127.0.0.1:8188`，支持 EasyAI/SillyTavern/Krita 直接接入，**不是 API 操作，是地址信息**
