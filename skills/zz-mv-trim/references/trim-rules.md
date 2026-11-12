# 粗剪规则与边界情况

## 1. 为什么不能直接按 `intended.start` 切

`clip_manifest.intended` 是**生成时的预期**，不是模型实际出片：

- Muse 实测切点会比 prompt 时间码早约 1s（`muse版` G1 预期 0/2.64/5.32，实际 0/1.92/4.42）；
- H3 输出时长会比请求多 0.3–0.5s；
- 同一 prompt 重跑，切点也会变。

所以主流程是：

```
intended.start  →  候选窗口之一
ffmpeg scene    →  真实切点
评分            →  选窗口
```

## 2. 选窗评分

对每个候选窗口 `[w, w+need]`：

```
score = |w - intended_start| + 0.5 × 窗口内硬切数
```

候选起点：

- `intended_start`（预期）；
- `0`、`clip_duration - need`（边界）；
- 每个真实切点 `c`；
- 每个 `c - need`（让窗口正好在切点结束）。

取 score 最小。含义：

- 平移 0.2s 换掉 1 个硬切，值得；
- 平移 0.8s 换掉 1 个硬切，不值得，宁可保留硬切并标 `crosses_cut`。

## 3. 置信度

```
high   : shift ≤ 0.12 且 cuts_inside == 0
medium : shift ≤ 0.60 且 cuts_inside ≤ 1
low    : 其他，或 coverage_short / missing_media / 无映射
```

`shift` 是实际入点相对预期入点的偏移。0.12s≈3帧（24fps），超过就可能是动作起点被切掉，所以要人看一眼。

## 4. 边界情况

### 4.1 素材比歌词短

`need > clip_duration` → `coverage_short` + `low`。不要冻结/慢放；处理顺序：

1. 换同句的另一条候选；
2. 回视频阶段重生成（提示词加“动作在前3秒完成”）；
3. 实在没有，剪辑师用相邻句镜头补。

### 4.2 窗口内必须跨切点

一句 3.2s，素材真实镜头只有 2.0s/1.2s 两段。保留硬切、标 `crosses_cut`，让剪辑师判断；不要为了“一镜到底”把窗口缩到 2.0s。

### 4.3 切点正好在窗口边界

`eps=0.12`：切点距窗口首/尾 <0.12s 不计入 `cuts_inside`。因为切在句子开头/结尾是正常的，不算“句中跳切”。

### 4.4 同一句有多条候选

`clip_manifest` 里多个 clip 的 `intended` 都可以包含同一 `line_id`。主流程会全部评分，选最优；`clip_id` 写进 manifest，方便回溯。

### 4.5 素材缺失

文件不存在 → 不切，进 `missing` 列表，报告里单列；不生成 0 字节文件。

### 4.6 fps 不一致

默认输出跟素材 fps（Muse 24fps、H3 24fps）。需要统一 30fps 时加 `--fps 30`；最终装配仍应按音乐时间轴补/裁最后一帧。

### 4.7 短句/长句

- 歌词 <1.5s：建议分镜阶段就合并到相邻句，不要硬切出一个闪帧；
- 歌词 >5s：建议分镜拆成 2 个镜头，粗剪按两个 line_id 处理；
- 这两条属于**分镜阶段规则**，粗剪不擅自合并/拆分，只按 timeline 执行。

## 5. 场景检测阈值

默认 `0.15`。经验：

- 硬切明显、镜头差异大：0.12–0.18；
- 同场景同人物、光线变化小：降到 0.10，否则漏检；
- 快速运镜/闪光多：升到 0.20–0.25，否则误检。

改阈值后重跑，对比 `cuts_inside` 和审片图；不要凭感觉调。

## 6. 输出与装配

- `trim/L01.mp4`：视频 only，无音轨；保留素材分辨率；
- `trim_manifest.json`：`duration` 是目标歌词时长，`actual_duration`/`frames` 是实际文件；
- 装配阶段用 `source_in/source_out` 或 `trim/L01.mp4` 都行；建议用 manifest 的 `source_in/out` 从原始素材重剪，避免二次转码；
- 最后一段按 `timeline.duration - 已用时长` 补/裁帧，和现有 `edit.py` 的 `frames[-1] += target - sum(frames)` 一致。

## 7. 后续增强

1. **语义匹配**：对 `low`/`crosses_cut` 的句子抽 3 帧，用 CLIP 对比歌词关键词；只在低置信度时跑，控制成本。
2. **候选对比图**：同一句多候选时，contact sheet 一行放 3 个候选，剪辑师点选。
3. **草稿成片**：`trim.py assemble` 直接按 timeline 拼 `preview.mp4`（音乐+字幕），剪辑师只审不剪。
4. **回填视频阶段**：粗剪发现 `coverage_short` 的句子，自动在 `storyboard.json` 标 `needs_regen`，工作台一键重跑。
