# 角色与风格提示词配套（帅哥/美女/治愈系）

> 先说清楚：**“好看”不能保证，只能提高命中率。** 真正起作用的是：角色卡 + 参考图 + 具体提示词 + 多候选 + 审核。只堆“beautiful / handsome”通常没用。

## 1. 五个杠杆

1. **角色卡**：先定脸、发型、体型、默认穿搭；不要每次从“一个美女”开始。
2. **参考图**：一张正面脸 + 一张全身穿搭，比 20 个形容词有效；不要用真实网红/明星的脸。
3. **具体描述**：脸型、眼睛、眉毛、鼻子、嘴唇、皮肤质感、妆发、服装材质、光线、镜头。
4. **多候选**：每个角色至少 4 张，拼成 2×2 对比图，选一张再锁定。
5. **QA**：脸不崩、手不崩、服装不串、文字/水印不要；视频里脸不漂。

## 2. 角色卡字段

```yaml
cast_id: C01
gender: female
age: 24
face: 鹅蛋脸，杏眼，自然直眉，鼻梁细直，唇形柔和小巧
skin: 健康透亮，可见毛孔，不磨皮
hair: 深棕，侧分，自然微卷
makeup: 干净底妆，自然眉，蜜桃腮红，裸粉唇釉
body: 165cm，匀称，肩颈舒展
outfit: 白色坑条针织，高腰阔腿牛仔，驼色风衣，金色耳环
palette: 暖米色
vibe: 松弛、自信、小红书穿搭博主
```

同一 `cast_id` 的 role card 一旦锁定，资产和所有视频段都引用它；换装只换 `outfit_id`。

## 3. 通用角色三视图模板（MOSS）

MOSS 的角色三视图规则：左格正面头肩、中格正面全身但**头部完全不入画**、右格背面全身；纯色无缝背景；不要四视图。下面模板可直接用，`{...}` 用风格包替换。

### 3.1 中文块

```text
用途：角色三视图，用于后续视频角色一致性参考。
画风：写实电影感，柔和自然光，真实皮肤纹理，不磨皮。
版式：横版 16:9，三格等宽。左格：正面头肩特写，完整五官，中性表情；中格：正面全身，从锁骨/领口以下开始，头部完全不入画，不出现脸、头发、脖颈断面；右格：背面全身，展示发型背面和服装背面。三格同一人、同一套服装、同一光线、同一比例，脚底对齐；纯色无缝背景；不要四视图，不要额外分格。
锚点：{face}；{hair}；{body}；穿 {outfit}。
姿态：自然站姿，双臂自然下垂，双脚与肩同宽。
背景：{solid_bg} 纯色无缝背景，无道具，无环境。
布光：{lighting}，正面主光加轻微侧光，保留皮肤纹理和发丝。
文字政策：无文字、无水印、无 logo。
负面：不要四视图、不要加格、不要换装、不要换人、不要中格出现脸/头发/脖颈断面、不要畸形手、不要多余手指、不要塑料磨皮、不要文字水印 logo。
```

### 3.2 英文块

```text
Purpose: character turnaround sheet for video consistency reference.
Style: photoreal cinematic, soft natural light, realistic skin texture, no beauty retouch.
Layout: 16:9 horizontal, three equal panels. Left: front head-and-shoulders close-up, full facial features, neutral expression. Middle: front full-body, framed from collarbone/neckline down, head completely out of frame, no face, no hair, no neck cross-section. Right: back full-body, showing the back of the hair and outfit. Same person, same outfit, same lighting, same scale, feet aligned; seamless solid background; no four-view, no extra panels.
Anchor: {face_en}; {hair_en}; {body_en}; wearing {outfit_en}.
Pose: natural standing, arms relaxed at sides, feet shoulder-width.
Background: {solid_bg_en}, seamless, no props, no environment.
Lighting: {lighting_en}, frontal key with slight side fill, preserve skin texture and hair strands.
Text policy: no text, no watermark, no logo.
Negative: no four-view, no extra panels, no outfit change, no different person, no face/hair/neck cross-section in the middle panel, no deformed hands, no extra fingers, no plastic skin, no text/watermark/logo.
```

---

## 4. 风格包 A：小红书穿搭博主（女）

**气质**：松弛、干净、会穿，不像影楼。

| 字段 | 中文 | English |
|---|---|---|
| face | 24–28 岁，鹅蛋脸，杏眼，自然直眉，鼻梁细直，唇形柔和小巧 | 24–28, oval face, almond eyes, natural straight brows, slim straight nose, soft small lips |
| skin | 健康透亮，可见毛孔，不磨皮 | healthy dewy skin, visible pores, no retouch |
| hair | 深棕，侧分，自然微卷 | dark brown, side part, loose natural waves |
| makeup | 干净底妆，自然眉，蜜桃腮红，裸粉唇釉 | clean base, natural brows, peach blush, nude-pink gloss |
| body | 165cm，匀称，肩颈舒展 | 165cm, slim and balanced, relaxed shoulders |
| outfit | 白色坑条针织，高腰阔腿牛仔，驼色风衣，金色耳环，皮质肩包 | white ribbed knit, high-waist wide-leg jeans, tan trench, gold hoops, leather shoulder bag |
| solid_bg | 暖米色 | warm beige |
| lighting | 窗边自然日光，柔和侧光 | soft window daylight, gentle side light |

**视频主体块（H3/Muse 可嵌入）**

```text
Subject: C01, a 26-year-old East Asian woman, oval face, almond eyes, natural straight brows, dark brown side-parted loose waves, clean natural makeup with peach blush, wearing a white ribbed knit, high-waist wide-leg jeans and a tan trench, gold hoop earrings. Natural skin texture, no beauty filter.
Action: walking toward the camera, one hand holding the bag strap, relaxed confident smile.
Camera: 35mm, full-body to medium shot, slight low angle, gentle handheld sway.
Light: soft window daylight, warm neutral grade.
```

## 5. 风格包 B：小红书穿搭博主（男）

| 字段 | 中文 | English |
|---|---|---|
| face | 26–30 岁，瘦长脸，深色眼睛，直眉，下颌线清晰 | 26–30, slim face, dark eyes, straight brows, defined jawline |
| skin | 干净，自然肤色，不油光 | clean natural skin, no greasy shine |
| hair | 黑色短发，纹理抓松 | short black hair, textured |
| outfit | 白 T、海军蓝衬衫外套、直筒长裤、白球鞋、银色手表 | white tee, navy overshirt, straight trousers, white sneakers, silver watch |
| solid_bg | 浅灰 | light gray |
| lighting | 窗边柔光 | soft window light |

**视频主体块**

```text
Subject: C07, a 28-year-old East Asian man, slim face, dark eyes, straight brows, defined jawline, short textured black hair, wearing a white tee, navy overshirt, straight trousers and white sneakers. Natural skin texture.
Action: walking down a quiet street, hands in pockets, glancing at the camera.
Camera: 35mm, medium full shot, eye level, subtle handheld.
Light: soft overcast daylight, neutral grade.
```

## 6. 风格包 C：日系甜妹

| 字段 | 中文 | English |
|---|---|---|
| face | 20–24 岁，圆润小脸，大而清亮的眼睛，柔和小鼻，唇形饱满 | 20–24, soft round face, large clear eyes, small soft nose, full lips |
| skin | 白皙，清透，轻微红润 | fair clear skin, soft natural flush |
| hair | 深棕，空气刘海，低马尾 | dark brown, airy bangs, low ponytail |
| makeup | 蜜桃腮红，细内眼线，水光唇 | peach blush, subtle eyeliner, glossy lips |
| outfit | 浅色针织开衫，白色棉质连衣裙，帆布鞋 | pastel cardigan, white cotton dress, canvas shoes |
| solid_bg | 暖奶油色 | warm cream |
| lighting | 午后窗光，轻胶片颗粒 | warm afternoon window light, light film grain |

**视频主体块**

```text
Subject: C11, a 22-year-old East Asian woman, soft round face, large clear eyes, airy bangs, low ponytail, peach blush and glossy lips, wearing a pastel cardigan and white cotton dress. Natural skin texture, soft film grain.
Action: sitting by a window, tucking a strand of hair behind her ear, gentle smile.
Camera: 50mm, medium close-up, slow push-in.
Light: warm afternoon window light, low contrast.
```

## 7. 风格包 D：韩系欧巴

| 字段 | 中文 | English |
|---|---|---|
| face | 28–34 岁，瘦长脸，下颌线清晰，深色眼睛，直眉 | 28–34, slim face, sharp jawline, dark eyes, straight brows |
| skin | 干净，哑光，自然肤色 | clean matte skin, natural tone |
| hair | 黑色，逗号刘海 | black hair, comma fringe |
| outfit | 黑色高领毛衣，长款羊毛大衣，剪裁长裤 | black turtleneck, long wool coat, tailored trousers |
| solid_bg | 深灰 | dark gray |
| lighting | 柔光箱 + 冷色轮廓光 | softbox with cool rim light |

**视频主体块**

```text
Subject: C15, a 31-year-old East Asian man, slim face, sharp jawline, dark eyes, straight brows, black comma fringe, wearing a black turtleneck and long wool coat. Clean matte skin.
Action: adjusting his coat cuff, looking toward the city lights.
Camera: 85mm, medium close-up, shallow depth of field, slow dolly.
Light: softbox key, cool rim light, night bokeh.
```

## 8. 风格包 E：清爽少年（帅哥）

| 字段 | 中文 | English |
|---|---|---|
| face | 20–25 岁，鹅蛋脸，眼睛明亮，自然眉，浅肤色 | 20–25, oval face, bright eyes, natural brows, light skin |
| hair | 黑色短发，轻微凌乱 | short black hair, slightly messy |
| outfit | 白 T、浅蓝衬衫、灰色直筒裤、白球鞋 | white tee, light blue shirt, gray straight trousers, white sneakers |
| solid_bg | 浅蓝灰 | pale blue-gray |
| lighting | 清晨窗光 | morning window light |

**视频主体块**

```text
Subject: C18, a 23-year-old East Asian man, oval face, bright eyes, natural brows, short slightly messy black hair, wearing a white tee, light blue shirt and gray trousers. Natural skin texture.
Action: putting on headphones, looking up with a light smile.
Camera: 50mm, medium shot, eye level, static.
Light: clean morning window light.
```

## 9. 风格包 F：清冷知性 / 御姐（美女）

| 字段 | 中文 | English |
|---|---|---|
| face | 30–36 岁，瘦长脸，杏眼，眉形清晰，唇色偏玫瑰 | 30–36, slim oval face, almond eyes, defined brows, muted rose lips |
| skin | 清透，哑光，细纹自然 | clear matte skin, natural fine lines |
| hair | 黑色，低发髻或直发 | black hair, low bun or sleek straight |
| outfit | 象牙白真丝衬衫，黑色剪裁长裤，细金饰 | ivory silk shirt, black tailored trousers, minimal gold jewelry |
| solid_bg | 冷灰 | cool gray |
| lighting | 侧窗光，低对比 | side window light, low contrast |

**视频主体块**

```text
Subject: C21, a 33-year-old East Asian woman, slim oval face, almond eyes, defined brows, muted rose lips, sleek black low bun, wearing an ivory silk shirt and black tailored trousers. Natural matte skin.
Action: turning from the window, holding a cup, calm direct gaze.
Camera: 85mm, medium close-up, static, shallow depth of field.
Light: soft side window light, cool neutral grade.
```

## 10. 风格包 G：治愈系电影（不绑定性别）

**适用**：日常、慢节奏、独白、产品露出不硬。

| 字段 | 中文 | English |
|---|---|---|
| face | 自然脸，淡妆，保留小雀斑/细纹 | natural face, minimal makeup, subtle freckles/fine lines |
| hair | 自然发色，低马尾或松散短发 | natural hair color, low ponytail or loose short hair |
| outfit | 亚麻衬衫、针织开衫、棉质长裙/长裤 | linen shirt, knit cardigan, cotton dress/trousers |
| palette | 低饱和绿、琥珀、米白 | muted green, amber, cream |
| lighting | 窗边自然光，轻胶片颗粒 | natural window light, light film grain |
| camera | 35mm，固定或极慢推 | 35mm, static or very slow push |

**视频主体块**

```text
Subject: C24, a 29-year-old East Asian person, natural face with minimal makeup and subtle freckles, loose low ponytail, wearing a linen shirt and knit cardigan. Natural skin texture, light film grain.
Action: pouring tea by the window, pausing to look outside, quiet expression.
Camera: 35mm, medium wide shot, static, slow push-in at the end.
Light: soft window light, muted green-amber grade.
```

---

## 11. 通用负面词

```text
deformed hands, extra fingers, missing fingers, fused fingers, twisted limbs, bad anatomy, double face, cross-eyed, asymmetric eyes, plastic skin, over-smoothed skin, waxy skin, harsh HDR, overexposed, text, watermark, logo, brand mark, cartoon, anime, 3D render, low resolution, blurry face, extra people, duplicate subject
```

中文提示词可对应写：

```text
不要畸形手、多余手指、缺指、粘连手指、扭曲肢体、错误解剖、双脸、斗鸡眼、双眼不对称、塑料磨皮、蜡像皮肤、过度 HDR、过曝、文字、水印、logo、品牌标、卡通、动漫、3D 渲染、低清、脸部模糊、多余人物、重复主体
```

## 12. 视频提示词怎么接

- **H3**：把上面的 `Subject` 段放进 `integrated_multimodal_description` 的主体描述，再按 H3 官方结构补动作、环境、镜头、声音；不要只写“美女在走路”。
- **Muse**：写成 60–350 字自然语言：主体锚定 → 一个主线动作 → 镜头 → 光线 → 声音 → 文字处理。10s 内只安排一个动作 + 一个镜头运动。
- **参考图**：角色一致性优先用参考图/首帧；Muse 参考图字段尚未验证，关键项目先用 H3 多参考或首帧图生视频。

## 13. 候选与 QA

1. 每个角色先生成 **4 张**，拼 2×2 对比图；不要一张就定。
2. 看脸：眼睛对称、瞳孔正常、牙齿自然、耳朵/发际线不崩。
3. 看手：手指数量、关节、拿道具的手。
4. 看服装：领口、缝线、图案、logo；不要出现真实品牌。
5. 看画质：皮肤有纹理、不塑料、不蜡像、不过曝。
6. 视频：脸不漂、口型对、动作连贯、首尾帧不跳。
7. 选中后把角色卡和参考图锁定；后续段落只引用，不重新描述一张新脸。

## 14. 法律与边界

- 不要用真实明星、网红、客户代言人的脸做“换脸”或高度相似角色；用虚构角色卡。
- 不要生成真实品牌 logo、校徽、车牌、手机号。
- 参考图如果是客户素材，确认授权范围；不要把客户素材提交到公开仓库。
