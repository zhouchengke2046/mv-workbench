# 批量视频换人（原 rh-batch-video-replace）

> 2026-11-03 并入 `zz-runninghub-cli`。工作流 `2099805997966643202`（人物替换单人稳定版｜MiniMax H3）。
> 本文件保留完整 recipe；原独立 skill 已归档，不再单独安装。

## 完整 recipe

把一批视频片段里的出镜人物替换成指定人物图，逐段调用 RunningHub 的 H3 换人工作流，成片自动换回原始音轨。

> ⚠️ **本文档只有流程，不含脚本**（实测核查 2026-09-17）
> 下文 §三 与 §七 引用的 `tools/batch_replace.py`、`tools/cut_by_pause.py`、`tools/normalize_clips.py`
> **既不在本仓库、也不在本机任何路径下**。
> 使用建议：
> - **可手工执行的部分照用**：§一 参数、§二 `api/` 前缀（最关键）、§四 固有限制、§五 已排除的坑、§六 排查接口 —— 用 curl / httpx 直调 API + ffmpeg 即可跑通
> - **需批量自动化时**：按 §三 的流程自行实现脚本；**脚本缺失不是任务失败的原因，不要往这个方向排查**
>
> 待办：若脚本仍在某处，补录到 `zz-runninghub-cli/scripts/` 下并在此回指。

## 一、前置条件

| 项 | 值 |
|---|---|
| 工作流 | `2099805997966643202`（人物替换单人稳定版｜Minimax H3） |
| 输入节点 | `137.image`（人物图）、`165.video`（源视频） |
| 输出 | `node 92`（SaveVideo，mp4） |
| 成片规格 | 768×1376 / 24fps / 含 H3 原生音频 |
| 单段耗时 | 约 370~680 秒（视时长） |
| 单段消耗 | 约 36~50 RH币 |

**账号**：用余额充足的消费级 key，通过 `mvwb keys set runninghub` 配置。
⚠️ 环境变量 `RUNNINGHUB_API_KEY` 会覆盖配置文件，跑之前先 `rh auth show` 确认。

## 二、🔴 最关键的一条：上传文件名必须带 `api/` 前缀

```python
# 上传
r = httpx.post(f"{HOST}/task/openapi/upload",
               data={"apiKey": KEY, "fileType": "input"},
               files={"file": (name, fh)}).json()
field_value = r["data"]["fileName"]      # → "api/<sha256>.mp4"

# 提交时原样填入，绝对不要 split("/")！
nodes = [{"nodeId": "137", "fieldName": "image", "fieldValue": img_field},
         {"nodeId": "165", "fieldName": "video", "fieldValue": vid_field}]
```

**去掉 `api/` 前缀会静默失败**：工作流读不到文件，H3 主链整条不进入执行图，任务 10~40 秒"秒退"、状态却是 SUCCESS、只花 1~7 RH币、产物是个无关小文件，**且完全不报错**。

**判别标准**：
| | 前缀正确 ✅ | 缺前缀 ❌ |
|---|---|---|
| 耗时 | 180~700s | **10~40s** |
| 消耗 | 36~235 RH币 | **1~7 RH币** |
| 产物 | mp4 + zip | 只有无关小文件 |

> 工作流 JSON 里节点默认值显示为**纯 hash**（如 `590e440f….mp4`），那是 RH 内部存储形式；**提交时要给 `api/<hash>` 全名**。

## 三、完整流程

```
1. 准备素材
   ├─ 人物图：任意图（PIL/ffmpeg 预处理成 PNG/JPG 均可）
   └─ 视频源：**优先用 1080p 原始分片拼接**，不要用 720p 转码版
        ffmpeg -f concat -safe 0 -i list.txt -c copy hd.mp4

2. 按气口切段（≤10s，相邻重叠 1s 供拼接容错）
   tools/cut_by_pause.py <源> <输出目录> <段数> <重叠秒数> <目标段长>
   用 ffmpeg silencedetect=noise=-32dB:d=0.12 + 贪心吸附静音段中点

3. 逐段提交（tools/batch_replace.py）
   ├─ 上传人物图（一次）+ 每段视频
   ├─ 提交：只传 137.image + 165.video
   │    ⚠️ 不传 frame_load_cap —— 节点 131 会自动按视频时长算 length，
   │       输出时长即等于源视频时长，换音轨不会错位
   ├─ 轮询 /task/openapi/status 直到 SUCCESS/FAILED
   ├─ 取 /task/openapi/outputs 里的 mp4 链接
   ├─ 失败重试（最多 4 次）
   └─ 下载成片

4. 换回原始音轨（关键后处理）
   ffmpeg -i H3成片.mp4 -i 源片.mp4 \
     -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest 输出.mp4

5. 校验
   ├─ 时长应与源片一致（±0.05s）
   ├─ 音轨采样率 = 源片的 44.1kHz（不是 H3 的 32kHz）
   └─ 抽样看画面：人物已替换 + 背景保留
```

## 四、必须知道的两个固有限制

### 1. H3 会自己编造画面文字
即使提交**已抹字幕**的素材，H3 仍会在画面中部生成乱码文字（如「趣家权研一卡嫩」），且**它的字幕与它生成的语音内容一致**（都是它自己编的）。**抹原字幕不能阻止它生成新文字。**

→ 处理方式：成片后**裁掉该区域**，或**重新压正确字幕**覆盖。

### 2. H3 的音频是重新生成的
`136` 节点的 `ref_video_audios ← 165` 只把源音轨当**音色参考**，不是内容复用。实测生成的语音是完全不通的乱码（原声「我们的这个眼霜啊」→ H3「我都出炼了」）。

→ 必须用第 4 步换回原始音轨。

## 五、踩过的坑（都验证过，别再试）

| 假设 | 结论 |
|---|---|
| 图片要先在网页端上传过 | ❌ 无关。上传是内容寻址（文件名=SHA256），API 与网页同一存储 |
| RH 审核拦截真人照片 | ❌ 无关。对照实验显示真人照片能成功、纯色图反而失败 |
| 工作流残缺、生成节点不在 | ❌ `getJsonApiFormat` 证明 58 节点完整 |
| 视频分辨率/编码/时间戳问题 | ❌ 720p 与 1080p、H.264 与 HEVC、start 偏移 都试过，非原因 |
| 账号等级/instanceType | ❌ 换过多个账号与档位，非原因 |
| 随机失败只能重试 | ❌ 是确定性的：**前缀带对了必成功** |

## 六、排查工具

```bash
# 读工作流完整结构（含全部节点/参数/连线）
POST /api/openapi/getJsonApiFormat
body: {"apiKey": "<key>", "workflowId": "<id>"}
→ data.prompt 是 ComfyUI API 格式 JSON 字符串（需二次 json.loads）

# 看任务真实失败原因（status 只说 FAILED 时不看这个等于瞎猜）
POST /task/openapi/outputs
body: {"apiKey": "<key>", "taskId": "<id>"}
→ FAILED 时返回 failedReason（含 traceback / node_name / node_id）

# WebSocket 实时执行链（比 outputs 信息全，能看出哪些节点没执行）
create 接口返回的 netWssUrl 可直接连，收到 executing / executed / progress 事件
```

## 七、工具脚本

> ⚠️ 下表三个脚本**均未入库**（本仓库无 `tools/` 目录），文档保留其存在时的接口说明，供重建时对齐。

| 脚本 | 状态 | 用途 |
|---|---|---|
| `tools/batch_replace.py` | ❌ 未入库 | 批量提交流程主程序（含重试、音轨还原、状态持久化） |
| `tools/cut_by_pause.py` | ❌ 未入库 | 按气口切分长视频 |
| `tools/normalize_clips.py` | ❌ 未入库 | 归零时间戳并重编码片段 |

**ffmpeg 路径**（本机无系统 ffmpeg 时）：
```bash
FF=$(python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -version
```
