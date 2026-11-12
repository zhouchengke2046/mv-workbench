# RunningHub（RH）

## 连接

- Base：`https://www.runninghub.cn`
- 鉴权：请求体里的 `apiKey`，或上传/任务接口的 `Authorization: Bearer <key>`
- Key：由 `mvwb keys set runninghub` 写入本地；`mvwb rh` 会注入 `RUNNINGHUB_API_KEY`

## 七步

```text
① 余额/队列检查
② POST /task/openapi/upload              → api/<sha256>.<ext>
③ 组装 nodeInfoList（只写要改的节点）
④ POST /task/openapi/create（workflow）
   POST /task/openapi/ai-app/run（AI 应用）
⑤ POST /task/openapi/status
⑥ POST /task/openapi/outputs
⑦ GET fileUrl 下载
```

完整参数、错误码、WebSocket、诊断见 [`runninghub-api.md`](runninghub-api.md)。

## MV 用到的模型

| 用途 | ID | 形态 | 备注 |
|---|---|---|---|
| ACE-Step 1.5 音乐 | `2075301815628943362` | AI 应用 | 节点 114 标签 / 115 歌词 / 116 秒；39 币/45s |
| MOSS 资产图 | `2116462203997081601` | workflow | 2MP、9:16；26 币/张 |
| H3 YZ 多参 | `2110943749894402050` | workflow | 6 图参考；约 19 币/4s |
| S2V 口型 | `1979183169033375745` | workflow | 8s、480×832，需超分 |
| Topaz 超分（可选） | `2099761219182882817` | AI 应用 | 先 720P 再超分 |

## 必看坑

1. 上传文件名保留 `api/` 前缀，否则任务 SUCCESS 但产物无关。
2. H3 的 `length` 是帧不是秒（24fps）。
3. 枚举字段显式覆盖英文值，不要用网页保存的中文标签。
4. 1080P 直出会 OOM，先 720P 再 Topaz。
5. 421 排队/817 不可取消；失败/超时仍可能扣费。
6. H3 会自编文字/语音；MV 里避开文字，后期统一音轨。

## 命令

```bash
./mvwb rh --app 2075301815628943362 --name song_v1 --overrides ov.json --out MV001/01_music
./mvwb rh --wf 2110943749894402050 --name G1 --nodes nodes.json --out MV001/03_segments
```
