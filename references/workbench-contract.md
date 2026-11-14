# Workbench DATA 契约

> 这是 `zz-mv-gongzuotai` 单 skill 的内部参考，不是独立 skill。工作台是只读展示 + 本地 Key 导入；agent 更新 `DATA`，页面不生成。

## 形态

- 单文件 `workbench.html`，CSS/JS/`DATA` 内联；**纯静态，双击或 `file://` 打开，不启动服务**。
- 无按钮、无接口、不联网；Key/余额只是 `DATA.keys` 快照，由 agent 用 `mvwb keys` 更新后重新 build。
- 左侧：原文（歌词/参考脚本）+ MV 列表；MV 行 = `MV001` + `已花 ¥X` + 三色环。
- 每 MV 四大项：音乐 / 资产图 / 脚本 / 分镜表；分镜表前两列：视频 / 视频段。
- 「参考脚本」是甲方提供的原文，原样展示、不改写；它的作用是供改编，不是让所有 MV 照搬。每条 MV 的「脚本」是据参考脚本改编出的本 MV 画面脚本，分镜表由它拆出。改编只动画面、不动歌词：**歌词固定不变，每个镜头的画面必须与它覆盖的歌词句匹配**。

## 项目目录

```text
workspaces/<project>/
├─ 原文/
│  ├─ lyric_original.md
│  ├─ story_script.md
│  └─ lyric.json
├─ workbench.html
└─ MV001/
   ├─ mv_manifest.json
   ├─ 00_script.md 画面脚本（据参考脚本改编）
   ├─ 01_music/song_v1.mp3, timeline_v1.json
   ├─ 02_assets/assets_v1.json, *.png
   ├─ 03_segments/segments_v1.json, G1_v1.mp4, G2_v1.mp4…
   └─ handoff_v1.json
```

## DATA

```json
{
  "meta": {"id": "D01", "title": "末班地铁", "generated_at": "2026-11-13 01:00", "batch": {"count": 3, "target_duration": 20, "style": "city_pop"}},
  "keys": {
    "runninghub": {
      "label": "RunningHub", "account": "账号备注",
      "configured": true, "masked": "••••abcd",
      "ok": true, "balance": 8971, "unit": "币",
      "wallet": 5.367, "wallet_unit": "CNY",
      "unlimited": false,
      "checked_at": "2026-11-13T01:00:00+08:00",
      "error": null
    },
    "router": {
      "label": "Router", "account": "",
      "configured": true, "masked": "••••wxyz",
      "ok": true, "balance": 4.0, "unit": "CNY",
      "wallet": null, "wallet_unit": null,
      "unlimited": false,
      "checked_at": "2026-11-13T01:00:00+08:00",
      "error": null
    }
  },
  "lyric": {"title": "末班地铁", "body": "[主歌 1]\n…"},
  "script": {"title": "末班地铁 · 参考脚本", "body": "人物\n…"},
  "mvs": [{
    "id": "MV001", "status": "ready", "target_duration": 20, "cost": 143, "spent": 143,
    "stages": {
      "music": {"status": "locked", "version": 1, "artifact": "01_music/timeline_v1.json", "cost": 39},
      "assets": {"status": "locked", "version": 1, "artifact": "02_assets/assets_v1.json", "cost": 104},
      "video": {"status": "draft", "version": 1, "artifact": "03_segments/segments_v1.json", "cost": 0}
    },
    "detail": {
      "music": [{
        "version": 1, "audio": "MV001/01_music/song_v1.mp3",
        "model": "ACE-Step 1.5", "cost": "≈¥3.9",
        "generated_at": "2026-11-13 00:40", "requested_duration": 20, "duration": 20.0,
        "status": "locked", "current": true
      }],
      "assets": [{
        "name": "女主三视图", "type": "角色",
        "url": "MV001/02_assets/role_female.svg",
        "resolution": "1024×1536", "model": "MOSS", "cost": "≈¥2.6",
        "generated_at": "2026-11-13 00:40"
      }],
      "script": {"body": "画面脚本 · MV001（据参考脚本改编）\n人物…\n开场｜…"},
      "storyboard": {
        "shots": [{"shot_id": "S01", "line_ids": ["L01"], "shot_size": "中景",
                   "camera": "固定机位", "visual": "末班地铁关上门…", "duration": 3.0}],
        "segments": [{
          "id": "G1", "shot_ids": ["S01", "S02"],
          "line_ids": ["L01", "L02", "L03", "L04"], "duration": 6.0,
          "videos": [{
            "url": "MV001/03_segments/G1_v1.mp4",
            "resolution": "720×1280", "model": "Muse Video Ext",
            "cost": "¥1.00", "generated_at": "2026-11-13 01:10", "duration": 6.0
          }]
        }]
      }
    }
  }]
}
```

## 规则

- `keys` 只存掩码/余额/查询时间，不含原始 key；由 `mv_keys.py balance --data data.json` 写入，再 build。
- `spent` = 历史累计花费（人民币）；左侧“已花 ¥X”/MV 头部“累计”用它。RunningHub 币→CNY 用 `config/models.json` 的 `fx.rh_coin` 折算。
- `music[].current` 标记当前版；历史版 `current:false`。
- 顶层 `script` 是参考脚本（甲方原文，原样展示）；`mvs[].detail.script.body` 是这条 MV 的画面脚本（据参考脚本改编），分镜表由它拆出；磁盘产物为 `MVxxx/00_script.md`。
- `segments[].videos` 按**生成顺序追加（旧版在前）**；`current:true` 的那条是当前视频，其余进历史，无标志时兜底取第一条；每条带分辨率/模型/费用/时间/时长。与音乐表（`current` 标志定当前/历史）同一套约定。
- `meta.batch.target_duration` 是用户设定的总时长；`mvs[].target_duration` 可覆盖。
- `music[].requested_duration` 是传给 ACE 的秒数；`music[].duration` 是实际输出。
- 分镜/段的 `duration` 在音乐出来前是计划值；音乐出来后按 `timeline` 更新为实际值。
- `segments[].duration` 是该段覆盖分镜的实际/计划总时长，必须 ≤10s。
- 资产/音频/视频 URL 都相对项目根；每个 MV 的文件放在自己的 `MVxxx/` 下。
- 工作台只显示环颜色；状态字段仍写 JSON/DATA 供 agent 判断。

## 状态

| 值 | UI | 含义 |
|---|---|---|
| `not_started` | 灰环 | 未生成 |
| `draft` | 琥珀环 | 有产物待审 |
| `locked` | 绿环 | 已定稿 |
| `stale` | 橙环 | 上游改动，需重跑 |
| `failed` | 红环 | 失败 |

## Agent 更新流程

1. 读 `mv_manifest.json`、`01_music/`、`02_assets/`、`03_segments/`；
2. 只重跑点名项，写 `*_v{n+1}.json`/媒体，不覆盖旧版；
3. 更新 `mv_manifest.json` 的 stages/history，`spent` 累加；
4. 音乐出来后对比 `target_duration` 与 `actual_duration`；偏差 >1s 或 >2% 先暂停；更新 segments 的实际时长；
5. 更新 `DATA`（或 `DATA.json` 后用 `build_workbench.py` 重建）；
6. 刷新页面。

## 边界

- 不粗剪、不拼片、不做成片。
- 不自动审核；用户提出修改后只重跑点名项。
- 不把客户歌词/脚本/素材提交到公开仓库。
