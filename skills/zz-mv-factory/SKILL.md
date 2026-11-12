---
name: zz-mv-factory
description: MV批量工作台（纯静态HTML + 可选本地Key配置服务，v1.2）。原文只读展示甲方歌词（歌名/主歌/副歌）与故事脚本（不拆分镜）；每条MV三大项：音乐列表、关键资产图、标准分镜表（前两列视频/视频段，视频段≤10s，可含1+镜，每段可多条视频历史）；静态版无按钮，服务版右上角只多Key配置（原始key不进HTML）。重跑/生成由agent直接操作JSON/媒体并更新workbench.html里的DATA。当用户说"MV批量工作台/重跑MV/更新工作台/标准分镜/原文/视频段/资产图元数据"时使用。
---

# zz-mv-factory · MV 批量工作台 · v1.2（2026-11-12）

> 本 skill = 只读模板的**数据契约 + agent 操作 SOP**。
> 不含后端/CLI/自动生成器；真实生成调用 `zz-runninghub-cli`，粗剪调用 `zz-mv-trim`。

## 模板形态（已定稿）

- 单文件 `demo/workbench.html`，CSS/JS/`DATA` 内联，`file://` 直接打开。
- 静态 `file://`：无后端/无 API/无 SQLite/无 fetch/无按钮。
- 本地服务版：只多“配置 Key”按钮/弹窗 + `/api/keys` `/api/balance`；生成/重跑仍走 agent。
- 左侧：**原文**（歌词 / 脚本）+ **MV 列表**。
  - MV 行：`MV001` + `已花 X 币` + 三色环；不显示模型标签、状态文字、3/3。
- 原文：歌词只读（歌名 + 主歌/副歌），脚本只读（故事脚本原文，不拆镜）。
- 每条 MV 三大项：**音乐 / 资产图 / 分镜表**。

## 打开方式

| 方式 | 打开 | Key 配置 | 其他交互 |
|---|---|---|---|
| 静态 | `file://.../workbench.html` | 无按钮，读 `DATA.keys` 快照 | 原文/MV 切换 |
| 服务版 | `mv_keys_server.py` → `http://127.0.0.1:<port>/go` | 右上角“配置 Key”弹窗 | 只多 Key 配置 |

- 服务版由仓库根 `scripts/mv_keys_server.py` 运行时注入按钮/弹窗；静态文件本身不含按钮/接口调用。
- 服务只绑 `127.0.0.1`；原始 key 只写 `~/.config/mv-workbench/keys.json`（0600）。

## 顶部 Key 状态与配置（v1.2）

- 静态版：右上角两个只读胶囊；没有按钮/弹窗。
- 服务版：胶囊旁多一个“配置 Key”按钮，点开弹窗写 keys.json；原始 key 不返回浏览器。
- 显示掩码、余额（币/¥/$）、状态点；颜色：绿=6h 内成功，琥珀=超过 6h，红=查询失败，灰=未配置。
- 悬停：账号、查询时间、错误、`~/.config/mv-workbench/keys.json` 路径。
- `DATA.keys` 是快照；刷新：`mv_keys.py balance --write` 或服务版弹窗“刷新余额”。

## 三大项的显示规则（冻结）

### 音乐
- 生成几次列几条；每条一个音频播放器。
- 小字：模型、生成费用、生成时间、`当前/历史`。
- **不显示时长**（音频里有）；**不显示审阅状态文字**。

### 资产图
- 只列关键图片：多次出现的角色/场景/产品。
- 名字在图片**上方**。
- 分辨率在图片**右下角**（角标）。
- 下方小字：模型、生成费用、生成时间。

### 分镜表
- 每 MV 一份：`MVxxx/02_storyboard/storyboard_v1.json`。
- 前两列固定：**视频**、**视频段**。
- 视频段：1 段可含 1+ 镜，**时长 ≤10s**；显示段号 + 时长 + 镜数。
- 视频：该段的生成视频站位；无视频显示“待生成”。
- 每段可多条视频：当前 + **历史折叠在视频列**。
- 视频分辨率在视频**右下角**；下方小字：模型、费用、时间、时长。
- 分镜列：镜号、对应句、景别、运镜、画面描述、时长；画面描述列宽 38%，时长列固定 60px。

## 状态（只显示环颜色）

模板**不显示**“已定稿/已过期/失败”等文字，只显示 MV 左侧**三段环**（音乐/资产/视频段）：

| 环色 | 状态 | 含义 |
|---|---|---|
| 灰 | `not_started` | 未开始 |
| 琥珀 | `draft` | 待审 |
| 绿 | `locked` | 已定稿 |
| 橙 | `stale` | 已过期（上游改了） |
| 红 | `failed` | 失败 |

状态字段仍写在 `mv_manifest.json` / `DATA` 里，供 agent 判断和重跑；只是不在 UI 显示文字。
`queued/running/approved/in_progress` 已从模板状态表删除（无生产者）；契约里保留，等真实异步队列再接。

## 数据路径

```
demo/
├─ workbench.html                         单文件模板
├─ 原文/
│  ├─ lyric_original.md                   歌词原文（歌名/主歌/副歌）
│  ├─ story_script.md                     故事脚本原文（不拆分镜）
│  └─ lyric.json                          line_id 映射（分镜用）
├─ MVxxx/
│  ├─ 01_music/timeline_v{n}.json, song_v{n}.mp3
│  ├─ 02_storyboard/storyboard_v1.json
│  ├─ 03_assets/…
│  └─ 04_clips/clip_manifest_v1.json, raw/, poster.jpg
└─ MV002…MV003/
```

## 模板 DATA 契约（agent 更新时保持这个形状）

```json
{
  "meta": {"id": "D01", "title": "末班地铁", "generated_at": "2026-11-12 19:15"},
  "keys": {
    "runninghub": {
      "label": "RunningHub", "account": "账号备注",
      "configured": true, "masked": "••••abcd",
      "ok": true, "balance": 8971, "unit": "币",
      "wallet": 5.367, "wallet_unit": "CNY",
      "unlimited": false,
      "checked_at": "2026-11-12T22:10:49+08:00",
      "error": null
    },
    "router": {
      "label": "Router", "account": "",
      "configured": false, "masked": "",
      "ok": false, "balance": null, "unit": "USD",
      "wallet": null, "wallet_unit": null,
      "unlimited": false,
      "checked_at": "2026-11-12T22:10:49+08:00",
      "error": "未配置 router.api_key"
    }
  },
  "lyric": {"title": "末班地铁", "body": "[主歌 1]\n…"},
  "script": {"title": "末班地铁 · 故事脚本", "body": "人物\n…"},
  "mvs": [{
    "id": "MV001", "status": "ready", "cost": 2031, "spent": 2222,
    "stages": {
      "music": {"status": "locked", "version": 2, "artifact": "01_music/timeline_v2.json", "cost": 35},
      "assets": {"status": "locked", "version": 2, "artifact": "03_assets/assets_v2.json", "cost": 156},
      "video": {"status": "locked", "version": 1, "artifact": "04_clips/clip_manifest_v1.json", "cost": 1840}
    },
    "detail": {
      "music": [{
        "version": 2, "audio": "MV001/01_music/song_v2.mp3",
        "model": "ACE-Step 1.5", "cost": "35 币",
        "generated_at": "2026-11-12 18:30:00",
        "duration": 53.87, "status": "locked", "current": true
      }],
      "assets": [{
        "name": "女主四视图", "type": "角色",
        "url": "assets/role_female.svg",
        "resolution": "1440×2560", "model": "MOSS", "cost": "26 币",
        "generated_at": "2026-11-11 16:52"
      }],
      "storyboard": {
        "shots": [{"shot_id": "S01", "line_ids": ["L01"], "shot_size": "中景",
                   "camera": "固定机位", "visual": "她坐在书桌前…", "duration": 2.64}],
        "segments": [{
          "id": "G1", "shot_ids": ["S01", "S02", "S03"],
          "line_ids": ["L01", "L02", "L03"], "duration": 7.96,
          "videos": [{
            "url": "MV001/04_clips/raw/G1.mp4", "poster": "MV001/04_clips/poster.jpg",
            "resolution": "720×1280", "model": "Muse Video Ext", "cost": "$0.024",
            "generated_at": "2026-11-11 21:53", "duration": 10.0
          }]
        }]
      }
    }
  }]
}
```

- `keys` 只存掩码/余额/查询时间，不含原始 key；由 `mv_keys.py balance --write` 更新。
- `checked_at` 是 ISO 本地时间；超过 6h 顶栏显示琥珀。
- `spent` = 历史累计花费；左侧“已花 X 币”和 MV 头部“累计”用它。
- `music[].current` 标记当前版；历史版 `current:false`。
- `segments[].videos` 第一条是当前视频，后面是历史视频；每条带分辨率/模型/费用/时间/时长。
- `segments[].duration` 是该段覆盖分镜的总时长，必须 ≤10s。

## Agent 重跑流程

1. 读 `MVxxx/mv_manifest.json` + `02_storyboard` + `04_clips`，确认上游 `locked`；
2. 用 `zz-runninghub-cli`（真实生成）/ `zz-mv-trim`（粗剪）重跑；写新版本 `*_v{n+1}.json`，不覆盖旧版；
3. 更新 `mv_manifest.json` 的 stages/history；新增历史成本累加到 `spent`；
4. 更新 `workbench.html` 里的 `DATA`：
   - `detail.music` 增/替换对应版本；
   - `detail.assets` 更新关键图与元数据；
   - `detail.storyboard.segments` 更新视频段/视频历史；
   - `stages`/`status`/`spent` 同步；
5. 刷新浏览器。

## 铁律

1. 原文只读，不改内容、不拆脚本。
2. 音乐 `locked` 后不可逆；换音乐=新建 MV。
3. 历史不覆盖；每次重跑新版本号。
4. 分镜表前两列视频/视频段；视频段≤10s；一段可含多镜。
5. 每段可多条视频；历史折叠；每条带分辨率/模型/费用/时间。
6. 资产只列关键图；名字在上、分辨率右下、模型/费用/时间在下。
7. 状态只显示环颜色；不显示状态文字/模型标签/3-3。
8. 模板本身不新增后端；服务版只多 Key 配置（`mv_keys_server.py`），生成仍走 agent。
9. 顶部 Key 只显示掩码/余额；原始 key 只存 `~/.config/mv-workbench/keys.json`，不进 HTML/DATA。

## 边界（不在本 skill 内）

- 真实模型的调用参数、重试、成本记账：走 `zz-runninghub-cli`。
- Key 配置/余额查询：走 `mvwb`（底层 `scripts/mv_keys.py`）。
- 粗剪算法：走 `zz-mv-trim`。
- 自动重建 HTML 的脚本：当前没有；agent 直接更新 `workbench.html` 的 `DATA`。
- 甲方真实歌词/故事脚本：当前是演示文本，替换 `原文/` 文件即可。
- 多用户/权限/发布：不属于静态模板。

## 版本

- v1.2（2026-11-12）：可选本地 Key 配置服务（服务版右上角按钮/弹窗、`/api/keys` `/api/balance`）；静态 `file://` 仍无按钮；原始 key 不进 HTML/DATA。
- v1.1（2026-11-12）：顶部只读 Key/余额胶囊；DATA 新增 `keys` 快照；原始 key 不进 HTML/DATA；Key 由 `mv_keys.py` 管理。
- v1.0（2026-11-12）：模板与数据契约冻结；三类状态只留环颜色；音乐去时长/状态文字；资产/视频分辨率右下角；分镜表固定列宽。
- 历史：v0.1 对话+HTML面板；v0.2 批量工作台；v0.3 静态模板。
