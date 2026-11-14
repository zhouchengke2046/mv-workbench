# MOSS 资产图提示词固定范式（MV 版）

> 资产图提示词**只有这一种写法**：中英双语 × 九段式 × 固定版式。写法继承漫剧壳（zz-manju-image-prompts），
> 按 MV 实测口径调整（MOSS 走 Router 任务协议，出图全部竖版）。写完必须过机检：
> `python3 scripts/check_asset_prompts.py <文件>`（exit 0 才交付）。

## 输入 → 产出

| 有 | 做法 | 产出 |
|---|---|---|
| 画面脚本 + 角色风格包（casting-style.md） | 逐资产写双语可复制正文 | `图片提示词.md`（每条 IMG-* 含 zh/en 两块） |
| 已有 `图片提示词.md` | 按本口径补齐/改写，保留 id 与文件命名 | 同文件 vN |

消费方：`scripts/providers/tokentech_task.py image --prompt <zh 正文>`（参数走 metadata.nodeInfoList：
4=主提示词、5=负向、16=seed）。**en 块是备份事实源**，默认提交 zh 正文。

## 三类版式（强制，缺一即不合格）

1. **角色 = 三视图**（竖版三格纵向）：上格正面头肩特写（完整五官）；中格正面全身但**头部完全不入画**
   （画面从下巴/领口以下开始，不出现脸、头发、脖颈断面）；下格背面全身（发型背面与服装背面）。
   三格同一人、同一服装、同一光线，比例一致、脚底对齐；**纯色无缝背景**；中性表情；无道具；**不要四视图**。
2. **道具 = 单视图纯底**（竖版居中产品图；必要时正+侧双格竖排）：同一物体同一光照；**纯色干净背景**；
   无手、无人、无环境。
3. **场景 = 空镜**（竖版 9:16）：**无人**（人物/动物一律不入画）、大全景或固定机位空镜、写清固定锚点与光向；
   品牌文字（如门头灯牌）允许且需逐字写明，其余无文字。

## 九段结构（zh 与 en 各自完整一遍）

【用途】→【画风】→【版式】→【锚点（身份/工业/地理）】→【姿态/状态】→【背景】→【布光】→【文字政策】→【负面】

- **负面四类**：版式误读（不要四视图/不要加格）、身份漂移（不要换装/不要换人）、画质（不卡通/不畸形/不磨皮）、文字（无文字/水印/logo）。
- **负向回弹警示**：不要把想排除的东西写成"颜色+形状"清单——实测会反向诱发（点名蓝色圆标后生成更大徽章）。
  用正向限定代替（"服面只有橙色条纹一种装饰"）。
- **连续性锁**：角色的固定辨识组合（如"米色针织开衫+帆布包"）原样写进两份正文，任何镜头不得增删改。

## 命名与落位

- 提示词 id：`IMG-<C|S|P><nn>`（C=角色、S=场景、P=道具）。
- 成品文件：`MV001/02_assets/<用途>_<名称>_v<n>.png`，与 `data.json → detail.assets[].url` 逐字一致。

## Router 出图参数（tokentech_task.py 已封装）

```bash
python3 scripts/providers/tokentech_task.py image \
  --prompt "<zh 正文>" \
  --negative "blurry, deformed hands, extra fingers, fused limbs, watermark, garbled text" \
  --seed <固定> --out MV001/02_assets/<name>_v1.png
```

- 节点映射：4=主提示词（--prompt）、5=负向（--negative）、16=seed（--seed）。
- 负向词固定基底：`blurry, deformed hands, extra fingers, fused limbs, watermark, garbled text`；
  版式类负向（不要四视图等）写在 zh 正文【负面】段，不进 --negative。
- QA 门禁与重跑见 `../step-contract.md` §4.2（fail 必跑 v2、warn 用户确认）。

## 样板

`examples/asset-character.md`、`examples/asset-scene.md`、`examples/asset-prop.md`（双语完整，可直接改锚点复用）。

## 机检

```bash
python3 scripts/check_asset_prompts.py 图片提示词.md [--json]
```

门（exit 0 才交付）：每条双块 ✓ 九段标签齐全 ✓ 角色三视图关键词 ✓ 道具纯底单视图 ✓
场景无人+锚点+光向 ✓ 负面非空 ✓。
