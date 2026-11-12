# Workbench DATA 契约

> 这是 `mv-gongzuotai` 单 skill 的内部参考，不是独立 skill。工作台是只读展示；agent 更新 `DATA`，页面不生成。

## 形态

- 单文件 `workbench.html`，CSS/JS/`DATA` 内联，`file://` 或本地服务打开。
- 静态版：无按钮、无接口。
- 服务版：只多右上角“配置 Key”按钮/弹窗 + `/api/keys` `/api/balance`。
- 左侧：原文（歌词/脚本）+ MV 列表；MV 行 = `MV001` + `已花 X 币` + 三色环。
- 每 MV 三大项：音乐 / 资产图 / 分镜表；分镜表前两列：视频 / 视频段。

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
   ├─ 01_music/song_v1.mp3, timeline_v1.json
   ├─ 02_assets/assets_v1.json, *.png
   ├─ 03_segments/segments_v1.json, G1_v1.mp4, G2_v1.mp4…
   └─ handoff_v1.json
```

## DATA

```json
{
  "meta": {"id": "D01", "title": "末班地铁", "generated_at": "2026-11-13 01:00"},
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
  "script": {"title": "末班地铁 · 故事脚本", "body": "人物\n…"},
  "mvs": [{
    "id": "MV001", "status": "ready", "cost": 143, "spent": 143,
    "stages": {
      "music": {"status": "locked", "version": 1, "artifact": "01_music/timeline_v1.json", "cost": 39},
      "assets": {"status": "locked", "version": 1, "artifact": "02_assets/assets_v1.json", "cost": 104},
      "video": {"status": "draft", "version": 1, "artifact": "03_segments/segments_v1.json", "cost": 0}
    },
    "detail": {
      "music": [{
        "version": 1, "audio": "MV001/01_music/song_v1.mp3",
        "model": "ACE-Step 1.5", "cost": "39 币",
        "generated_at": "2026-11-13 00:40", "duration": 20.0,
        "status": "locked", "current": true
      }],
      "assets": [{
        "name": "女主四视图", "type": "角色",
        "url": "MV001/02_assets/role_female.svg",
        "resolution": "1024×1536", "model": "MOSS", "cost": "26 币",
        "generated_at": "2026-11-13 00:40"
      }],
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

- `keys` 只存掩码/余额/查询时间，不含原始 key；由 `mv_keys.py balance --write` 或服务版刷新。
- `spent` = 历史累计花费；左侧“已花 X 币”/MV 头部“累计”用它。
- `music[].current` 标记当前版；历史版 `current:false`。
- `segments[].videos` 第一条是当前视频，后面是历史视频；每条带分辨率/模型/费用/时间/时长。
- `segments[].duration` 是该段覆盖分镜的总时长，必须 ≤10s。
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
4. 更新 `DATA`（或 `DATA.json` 后用 `build_workbench.py` 重建）；
5. 刷新页面。

## 边界

- 不粗剪、不拼片、不做成片。
- 不自动审核；用户提出修改后只重跑点名项。
- 不把客户歌词/脚本/素材提交到公开仓库。
