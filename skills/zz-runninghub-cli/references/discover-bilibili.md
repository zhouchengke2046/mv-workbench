# 从外部来源发现 RunningHub 工作流（原 zz-rh-discover）

> 2026-10-29 并入 `zz-runninghub-cli`。`{baseDir}` = 本 skill 目录；`{UPSTREAM}` 见 `references/rhcli-adapter.md`。


从外部内容源（当前：B 站视频）中提取 RunningHub 工作流链接，分析视频介绍的工作流功能，引导用户验证并入库。入库时调用 zz-runninghub-cli 的 `workflow add`，沉淀到跨 Agent 共享的 `~/.runninghub/profile.json`。

## 依赖

- **依赖**：本 skill 已内置 `rh_profile.py` / `rh_sdk.py`，并经 `{UPSTREAM}` 指路上游 `runninghub_app.py`，无需另装 zz-runninghub-cli。

## 唯一入口

```bash
python3 {baseDir}/scripts/rh_bili.py "<视频URL|BV号>" [--pages N] [--comments N] [--all]
```

脚本零第三方依赖（纯标准库），抓取视频标题/简介/评论区，扫描所有 RunningHub 链接，输出结构化 JSON。

## 使用流程

用户发 B 站视频链接（UP 主通常把 RunningHub 工作流链接放**简介或置顶/热评**）：

1. **抓取提取**：跑 `rh_bili.py "<URL>"`，拿到标题/简介/评论/链接列表
2. **功能分析**：根据**标题 + 简介**分析视频介绍的工作流功能，向用户复述确认（"这个视频介绍的是 XX 工作流，能做 YY"）
3. **节点验证**：对每个带 webappId 的链接，调用 `python3 {UPSTREAM}/scripts/runninghub_app.py --info <webappId>` 验证节点、确认输入类型（IMAGE/VIDEO/STRING）
4. **测试运行**：用户确认后 → `--run` 测试（**消耗 RH 币，需用户同意**）
5. **入库沉淀**：跑成功 → `python3 {baseDir}/scripts/rh_profile.py workflow verify <webappId>` + `workflow add <webappId> --task X --title ... --note ...` 入库

## 关键规则

1. **未登录仅能取到置顶/热评**（恰好是 UP 主放链接的位置）；要全量评论：配置 `BILI_COOKIE` 环境变量或 `~/.bilibili/cookie.txt`（内容为 `SESSDATA=xxx`）
2. 提取不到 webappId 的链接，向用户展示原始 URL 人工核对
3. **禁止直接 `--run` 未 `--info` 验证过的 webappId**（盲跑消耗 RH 币且可能失败）
4. Cookie 只用于读取公开评论，不写入任何持久化存储

## 输出格式（rh_bili.py 返回的 JSON）

```json
{
  "bvid": "BV1xxxx",
  "title": "视频标题",
  "owner": "UP主名",
  "desc": "视频简介（前 800 字）",
  "comment_count_scanned": 40,
  "cookie_used": false,
  "comment_coverage": "top-only(未登录仅能取到置顶/热评)",
  "workflow_links": [
    {"url": "https://www.runninghub.cn/ai-detail/123456", "webappId": "123456", "source": "desc"}
  ],
  "note": "webappId 为空的链接需人工核对；任何 webappId 在 run 前必须 runninghub_app.py --info 验证"
}
```

## 扩展位（未来来源）

当前只支持 B 站视频。未来可扩展：
- 热榜/推荐浏览（`runninghub_app.py --list --sort HOTTEST/NEWEST`）
- 其他社区/平台的工作流分享

新增来源时，在 scripts/ 下加对应脚本，SKILL.md 加对应流程即可。
