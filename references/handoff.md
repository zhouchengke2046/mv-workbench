# 视频段交付（handoff）

项目到视频段结束。剪辑拿 `handoff_v1.json` + 视频文件进入下一阶段。

## 目录

```text
MV001/03_segments/
├─ segments_v1.json
├─ G1_v1.mp4
├─ G1_v2.mp4     审核重跑的历史（当前版本由 segments_v1.json 指向）
├─ G2_v1.mp4
└─ handoff_v1.json
```

## handoff_v1.json

```json
{
  "mv_id": "MV001",
  "status": "ready",
  "music": "01_music/song_v1.mp3",
  "timeline": "01_music/timeline_v1.json",
  "segments": [
    {
      "segment_id": "G1",
      "line_ids": ["L01", "L02"],
      "music_start": 0.0,
      "music_end": 6.0,
      "duration": 6.0,
      "video_file": "03_segments/G1_v1.mp4",
      "model": "muse-video-ext",
      "resolution": "720x1280",
      "notes": "审核通过的当前版本"
    }
  ]
}
```

- `music_start/end` 来自 `timeline_v1.json`，不是分镜计划时长。
- `video_file` 是相对 MV 目录的路径；剪辑可直接按 `music_start` 对齐。
- 历史版本保留在 `03_segments/`，但 handoff 只给当前 `locked` 版本。
- 所有段 `locked` 后，`status` 才能写 `ready`。
- 可选再导一份 `handoff_v1.csv`，字段同上，方便表格导入。

## 交付前检查

- [ ] 每段 `duration ≤ 10s`
- [ ] `video_file` 存在且能播放
- [ ] `music_start/end` 与时间轴一致
- [ ] 段覆盖的 `line_ids` 不重不漏
- [ ] 当前版本是审核通过的版本
- [ ] 没有把 `stale`/`failed` 段写进 handoff
