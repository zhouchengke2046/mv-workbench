# 变体与差异化：让每条 MV 的角色、故事、音乐不一样

> 结论先说：**“每条都不一样”不能靠每次随机，要靠基因组 + 分配 + 去重 + 门禁。** 模型输出仍然要审核；这里保证的是“计划层不重复”，不是“模型每次都好看”。

## 1. 五个维度

每条 MV 在框架阶段固定一份 `genome`，至少覆盖：

| 维度 | 字段 | 例子 |
|---|---|---|
| 角色 | `cast_id` + `outfit_id` + `face_seed` | C03 / O07 / 3182 |
| 故事 | `story_id` + `premise` + `conflict` + `product_role` | S02 / 末班地铁错过站 / 是否回头 / 耳机是线索 |
| 音乐 | `genre` + `bpm` + `key` + `vocal` + `mood` + `instruments` | city pop / 88 / A minor / female soft / 夜雨 / 电吉他 |
| 视觉 | `pack` + `location` + `time` + `weather` + `palette` + `lens` | P01 / 地铁站台 / 夜 / 雨 / teal-amber / 35mm |
| 剪辑 | `rhythm` + `transition` | 慢切 / 叠化 |

`genome` 写进 `mv_manifest.json` 和 `DATA.mvs[].genome`；后续资产、视频都从它派生，不能到生成时再临时想。

## 2. 分配：不要随机，要分层抽样

### 2.1 先建池子

```text
cast_pool:    C01…C20   每个角色一张锁定角色卡（脸/发型/体型/默认穿搭）
outfit_pool:  O01…O08   每个角色可换的穿搭
story_pool:   S01…S10   故事模板（相遇/错过/误会/重逢/告别/日常…）
music_pool:   M01…M20   曲风/BPM/调式/人声/情绪/配器
visual_pool:  V01…V08   场景包（地铁/街道/便利店/天台/公寓…）
edit_pool:    E01…E05   节奏/转场
```

### 2.2 用“变体号”做确定性分配

`variant_id = L01-V037`。用变体号做哈希/取模，从各池取值；不要用 `random()`，否则重跑不可复现。

```text
cast    = cast_pool[hash(variant_id + "cast")    % len(cast_pool)]
outfit  = outfit_pool[hash(variant_id + "outfit") % len(outfit_pool)]
story   = story_pool[hash(variant_id + "story")  % len(story_pool)]
music   = music_pool[hash(variant_id + "music")  % len(music_pool)]
visual  = visual_pool[hash(variant_id + "visual")% len(visual_pool)]
edit    = edit_pool[hash(variant_id + "edit")    % len(edit_pool)]
```

### 2.3 冲突检查

对任意两条 MV，至少 3 个维度不同；同一批内禁止：

- 相同 `cast_id + outfit_id`（同一个人穿同一套）；
- 相同 `story_id + conflict`（同一个故事矛盾）；
- 相同 `genre + bpm 档 + vocal`（听起来像同一首）；
- 相同 `pack + location + palette`（画面像同一个场景）；
- 相同 `rhythm + transition`（剪起来像同一条）。

冲突就换池子里的下一个，不重新随机。

### 2.4 一个 5 条的示例

| MV | 角色/穿搭 | 故事 | 音乐 | 视觉 | 剪辑 |
|---|---|---|---|---|---|
| MV001 | C01 / O03 | S02 末班地铁错过站 | city pop 88 A minor 女声 | P01 地铁夜雨 teal-amber | 慢切/叠化 |
| MV002 | C07 / O01 | S05 便利店偶遇 | acoustic 72 C major 男声 | P04 便利店暖白 | 固定/硬切 |
| MV003 | C03 / O06 | S08 天台告别 | R&B 96 F# minor 女声 | P06 天台黄昏 amber | 跟拍/硬切 |
| MV004 | C12 / O02 | S01 雨中借伞 | indie rock 110 D major 男声 | P02 街道夜雨 blue-gray | 快切/闪白 |
| MV005 | C09 / O05 | S09 清晨重逢 | lo-fi 80 G major 女声 | P03 公寓清晨 cream | 慢推/叠化 |

## 3. 角色：一条 MV 内必须一致，跨 MV 必须不同

### 3.1 一条 MV 内

- 一个 `cast_id` 对应一张锁定角色卡（三视图 + 脸特写 + 服装）。
- 所有资产、所有视频段引用同一张角色卡；换装只在故事需要时发生，并记录 `outfit_id`。
- 视频段用首帧/参考图对齐；H3 多参考、Muse 参考图（字段待验证）优先用参考图而不是只靠文字。

### 3.2 跨 MV

- `cast_id` 尽量不重复；角色池小于 MV 数时，用 `cast_id + outfit_id + face_seed` 组成新身份。
- 如果要求“每个角色都长得不一样”，就必须为每条 MV 生成独立角色卡；这是成本项（MOSS 26 币/张），不是免费的。
- 同一演员连续做系列（同一客户/同一人设）是例外：允许同 `cast_id`，但换 `outfit_id` + 故事 + 场景，并在 genome 里标 `series_id`。

## 4. 故事：用模板槽位，不要每次从零写

每个故事模板固定 5 个槽位：

```text
钩子（前 3 秒） → 冲突（为什么停下来） → 转折（一个动作/一句话） → 产品角色（线索/道具/解决方案） → 余味（最后一个画面）
```

同一个模板，换槽位内容就算新故事；但 `template + conflict + ending` 不能完全一样。建议用故事 logline 做一次文本相似度检查（embedding 余弦 < 0.85 作为起点，人工复核）。

## 5. 音乐：先分配，再试听

- 每个 `music_id` 固定：genre/subgenre、BPM 档、调式、人声类型、情绪、3 个配器。
- 同批至少保证 `genre` 或 `BPM 档` 或 `vocal` 有一个不同；不要 10 条全是“city pop 88 BPM 女声”。
- 生成后用音频指纹/embedding 做近似去重；没有工具就人工 A/B：前 10 秒是否听起来像同一首。
- 音乐锁定后不换歌；换歌 = 新建 MV。

## 6. 去重与门禁

| 层 | 检查 | 不通过 |
|---|---|---|
| 框架 | 差异化表：cast/outfit/story/music/visual/edit 是否有重复组合 | 停，换组合 |
| 音乐 | 同批 genre+BPM+vocal 重复；音频近似 | 重生成 |
| 资产 | 同 MV 角色脸/发型/服装一致；跨 MV 角色卡不同 | 重跑或换 cast |
| 视频 | 同 MV 角色不漂；跨 MV 首帧构图不雷同 | 重跑 |
| 人工 | 10 条里抽 2 条看“像不像同一条” | 整批回退 |

## 7. 和现有契约的关系

- `references/step-contract.md` 的 Step 3 必须输出 `genome` 和差异化表；没有表不算框架完成。
- `references/workbench-contract.md` 的 `DATA.mvs[].genome` 保存同一份；工作台只展示，不重算。
- 角色卡的图片规则见 `references/prompts/casting-style.md` 和 `references/prompts/moss.md`。
