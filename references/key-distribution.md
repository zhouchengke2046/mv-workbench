# Key 发放与导入（老师 → 学生）

## 推荐方式：项目目录里的一个 JSON

**老师**生成一个 `keys.incoming.json`，私下发给学生。  
**学生**把它放到项目根目录：

```text
workspaces/<项目名>/
├─ 原文/
├─ keys.incoming.json     ← 放这里
├─ data.json
└─ workbench.html
```

**学生对 agent 说**：

```text
Key 文件在项目根目录的 keys.incoming.json。
请帮我导入，导入后删除这个文件。
```

**agent 执行**：

```bash
mvwb keys import --file workspaces/<项目名>/keys.incoming.json --delete-source
```

导入后：

- Key 写入 `~/.config/mv-workbench/keys.json`（0600）；
- 下载/发放的 JSON 被删除；
- 所有项目共用这一份全局 Key，不用每个项目重复导入；
- 再查余额、重建工作台。

## 为什么不建议“直接发给 agent”

- 聊天附件可能被复制到临时目录，路径不固定；
- Key 会进入对话历史/日志，事后难清理；
- 项目目录里的文件路径确定，agent 可以校验、导入、删除，形成闭环。

如果只能发附件：让 agent 先把附件保存到项目根目录的 `keys.incoming.json`，再按上面流程导入，不要直接读聊天里的 Key。

## 统一 JSON 格式

**格式必须统一**，否则 agent 每次都要猜字段。使用这个结构（`config/keys.distribute.example.json`）：

```json
{
  "mv_keys_import": 1,
  "issued_to": "student-001",
  "issued_at": "2026-11-14",
  "expires_at": "2026-12-31",
  "runninghub": {
    "api_key": "rh-xxxxxxxx",
    "label": "RunningHub",
    "account": "student-001"
  },
  "router": {
    "api_key": "sk-xxxxxxxx",
    "base_url": "https://router.kcacher.top"
  }
}
```

字段说明：

| 字段 | 必填 | 说明 |
|---|---|---|
| `mv_keys_import` | 建议 | 固定 `1`；导入 watcher 只认带这个标记的文件 |
| `issued_to` | 建议 | 学生编号/姓名，便于对账 |
| `issued_at` / `expires_at` | 可选 | 发放/过期日期；过期后由老师作废 |
| `runninghub.api_key` | 二选一 | RunningHub Key |
| `router.api_key` | 二选一 | Router Key |
| `router.base_url` | 可选 | 默认 `https://router.kcacher.top` |

- 两个 Key 至少给一个；给两个最省事。
- `mvwb keys import` 会忽略未知字段，所以以后加 `note`、`group` 不影响。
- 不要用 `{ "runninghub_key": "...", "router_key": "..." }` 这种自定义扁平格式；虽然旧代码兼容，但统一用上面的嵌套格式。

## 发放建议

- **一人一份 Key**，不要所有学生共用一个；否则无法单独停用、无法对账。
- 文件不要进 Git；`workspaces/` 默认被忽略，根目录也加了 `keys.incoming.json` / `mv-keys-import*.json`。
- 发完后让学生导入并删除；老师侧保留发放记录（谁、何时、哪个 Key）。
- 学生换电脑：重新发一份，或从旧电脑的 `~/.config/mv-workbench/keys.json` 迁移。
- 学生把 Key 发到群里/对话里：提醒作废重发。

## 和工作台“配置 Key”的关系

- **老师统一发放**：用本文件的 `keys.incoming.json`，最省事。
- **学生自己买 Key**：用工作台右上角“配置 Key”下载 `mv-keys-import.json`，再让 agent 导入；格式与上面兼容。
- **没有 agent 在旁边**：双击 `setup-keys.command` / `.cmd` 手动输入。
