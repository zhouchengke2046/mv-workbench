# Key 发放与导入（老师 → 学生）

## 推荐方式：项目目录里的一个 JSON

**老师**生成一个 `zz-keys.json`，私下发给学生。  
**学生**把它放到项目根目录：

```text
workspaces/<项目名>/
├─ 原文/
├─ zz-keys.json     ← 放这里
├─ data.json
└─ workbench.html
```

**学生对 agent 说**：

```text
Key 文件在项目根目录的 zz-keys.json。
请帮我导入，导入后删除这个文件。
```

**agent 执行**：

```bash
mvwb keys import --file workspaces/<项目名>/zz-keys.json --delete-source
```

导入后 Key 写入 `~/.config/mv-workbench/keys.json`（0600），发放文件被删除；所有项目共用这份全局 Key。

## JSON 只需要两个字段

```json
{"runninghub": "rh-xxxxxxxx", "router": "sk-xxxxxxxx"}
```

就这两行。`mvwb keys import` 直接认。两个 Key 至少给一个；给两个最省事。Router 地址不写就用默认 `https://router.kcacher.top`。

如果只有一个 Key：

```json
{"runninghub": "rh-xxxxxxxx"}
```

或：

```json
{"router": "sk-xxxxxxxx"}
```

## 可选：需要登记/自动拾取时才加

只有在“想用 `mvwb keys watch` 自动拾取”或“要按学生对账”时，才加下面这些字段；不加也能手动导入。

```json
{
  "mv_keys_import": 1,
  "issued_to": "student-001",
  "expires_at": "2026-12-31",
  "runninghub": "rh-xxxxxxxx",
  "router": "sk-xxxxxxxx"
}
```

| 字段 | 用途 |
|---|---|
| `mv_keys_import: 1` | watcher 只自动拾取带这个标记的文件；手动导入不需要 |
| `issued_to` | 发放对象，方便对账；目前只记录，不校验 |
| `expires_at` | 过期日期；目前只记录，不自动拒绝，过期由老师侧作废 |

## 为什么不建议“直接发给 agent”

- 聊天附件可能落到临时目录，路径不固定；
- Key 会进入对话历史/日志，事后难清理；
- 项目目录里的文件路径确定，agent 能校验、导入、删除，形成闭环。

如果只能发附件：让 agent 先把附件保存成项目根目录的 `zz-keys.json`，再导入，不要直接读聊天里的 Key。

## 发放建议

- **一人一份 Key**，不要所有学生共用一个；否则无法单独停用、无法对账。
- 文件不要进 Git；`workspaces/` 默认忽略，根目录也忽略了 `zz-keys.json` / `mv-keys-import*.json`。
- 学生换电脑：重新发一份，或迁移旧电脑的 `~/.config/mv-workbench/keys.json`。
- 学生把 Key 发到群里/对话里：提醒作废重发。

## 发放节奏

- **初期只发 Router Key**：`zz-keys.json` 里只有 `{"router": "..."}`；方便统一算成本（工作台也只显示 Router 余额）。
- **备用 Key 按需另发**：中转站连续出问题、短时间修不好时，再发一份含 `runninghub` / `apimart` 字段的 `zz-keys.json`；学生放到项目根目录导入即可，导入后自动启用备用平台。

## 和工作台“配置 Key”的关系

- **老师统一发放**：用 `zz-keys.json`，两行 JSON，最省事。
- **学生自己买 Key**：用工作台右上角“配置 Key”下载 `mv-keys-import.json`，格式兼容。
- **没有 agent 在旁边**：双击 `setup-keys.command` / `.cmd` 手动输入。
