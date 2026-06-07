# Cursor Current Thread Tool Registry Check

本文档说明 **MCP server 在 CLI / Settings 层 ready** 与 **当前 Agent 对话线程实际暴露工具** 之间的差异，以及如何排查 Cursor 浏览器任务失败。

相关 runbook：[`docs/cursor_browser_ui_runbook.md`](cursor_browser_ui_runbook.md)

---

## 核心原则

### 1. 终端里的 MCP ready 只能说明 server 可用

`cursor-agent mcp list`、`npm run check:mcp`、`npm run check:cursor-mcp` 等命令检查的是：

- `.cursor/mcp.json` 配置是否正确；
- Cursor CLI 是否能连接到 MCP server；
- Settings 中 server 是否已批准。

**这些都不保证当前 Agent 对话线程已注册对应工具。**

### 2. 当前 Agent 对话必须实际暴露工具

Agent 能否调用 `browser_navigate`、`list_pages`、`create_screen` 等，取决于 **当前对话启动时** 加载的工具注册表。

必须在对话中直接观察工具列表，或尝试调用并确认成功——不能只看配置文件。

### 3. Multitask 子 Agent 可能没有继承 Workspace MCP

Cursor **Multitask** 模式启动的后台子 Agent 通常：

- 不继承父对话的 Workspace MCP 注册表；
- 缺少 `chrome-devtools`、`playwright`、`wechat-chrome-session`、`stitch` 等工具；
- 可能只能看到 Cursor 内置 `browser_tabs` 或有限工具集。

**浏览器控制任务禁止使用 Multitask。** 见 `.cursor/rules/no-multitask-for-browser.mdc`。

### 4. 旧对话可能仍停留在批准前的工具注册表

常见场景：

- 用户在 Settings 中批准了新 MCP，但 **未完全退出 Cursor**；
- 继续使用 **旧 Agent 对话** 执行浏览器任务；
- 对话内工具列表仍是批准前的快照。

表现：`cursor-agent mcp list` 显示 ready，但 Agent 报 `server does not exist` 或找不到工具。

### 5. 正确处理方式：完全重启 Cursor 并新开普通 Agent 对话

推荐恢复步骤：

1. **完全退出 Cursor**（Cmd+Q / 关闭所有窗口，不是仅 Reload Window）。
2. 重新打开本仓库。
3. Settings → Tools & MCP → 确认所需 server 为 **Enabled / Ready**。
4. **新建** 普通前台 Agent 对话（**不要** 使用 Multitask）。
5. 在对话开头让 Agent 确认当前线程是否暴露目标 MCP 工具。
6. 若仍缺失，检查 `.cursor/mcp.json` 并再次完全重启。

### 6. Server 名称连字符与 underscore alias

部分 Cursor 版本在路由带连字符的 server 名称时可能出现问题（例如 `wechat-chrome-session`、`chrome-devtools`）。

若确认 CLI ready 但对话线程仍无法路由到正确 server，可在 `.cursor/mcp.json` 中 **增加 underscore alias**（复制相同配置，使用下划线名称）：

```json
"wechat_chrome_session": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect", "..."]
}
```

**注意：**

- 不要覆盖已有配置；alias 是额外条目。
- 必须在本文档或 runbook 中记录 alias 用途。
- 本仓库当前主配置使用连字符名称；仅在确认路由问题时添加 alias。

---

## 排查表

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| `cursor-agent mcp list` 显示 ready，但对话中 server does not exist | 当前线程未继承工具注册表 | 完全退出 Cursor，新建普通前台 Agent 对话 |
| Multitask 中缺少 MCP 工具 | 子 Agent 未继承 Workspace MCP | 禁用 Multitask；改用普通前台 Agent |
| `wechat-chrome-session` ready 但无法调用 | 工具未暴露给当前线程或名称路由问题 | 新建前台 Agent；必要时增加 `wechat_chrome_session` alias |
| playwright 打开的是未登录页面 | Playwright 新开隔离浏览器（`--isolated`） | 微信任务改用 `wechat-chrome-session`；本地 Web 用 playwright 正常 |
| chrome-devtools 不能接管现有页面 | Chrome 未开启 remote debugging 或线程没有工具 | 按 [`wechat_chrome_session_runbook.md`](wechat_chrome_session_runbook.md) 开启 remote debugging；重启 Cursor |
| Agent 只能看到 `browser_tabs` / localhost 页面 | 使用了 Cursor 内置浏览器，非 Workspace MCP | 停止任务；确认 chrome-devtools / playwright MCP 已加载到新对话 |
| Stitch 设计任务无 stitch 工具 | STITCH_API_KEY 未设置或线程未注册 | 设置 `STITCH_API_KEY` 环境变量；完全重启 Cursor；新建对话 |
| `npm run check:mcp` 通过但浏览器任务仍失败 | 只检查了配置层，未检查对话线程 | 运行 `npm run check:cursor-mcp` 作辅助；重点检查当前对话工具列表 |

---

## Agent 自检脚本（CLI 辅助）

以下命令 **不能替代** 对话线程检查，仅作配置层辅助：

```bash
bash scripts/check_cursor_mcp_status.sh
npm run check:cursor-mcp
npm run check:mcp
npm run check:stitch
```

脚本输出末尾会提示：

> 该脚本只检查 CLI 层，不代表当前 Agent 对话线程已暴露工具。

---

## BLOCKED 标准输出

当 Agent 确认当前线程缺少所需 MCP 工具时，应输出：

```text
BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY

缺失：<server-name>
原因：当前 Agent 对话线程未暴露该 MCP 的原生工具。

用户操作：
1. 完全退出 Cursor
2. 重新打开仓库
3. Settings → Tools & MCP 确认 ready
4. 新建普通前台 Agent（禁用 Multitask）
5. 重新执行任务

文档：docs/cursor_tool_registry_check.md
```

**不得** 在 BLOCKED 状态下继续假装执行浏览器检查或 UI 验证。

---

## 与本仓库 MCP 的对应关系

| Server | 配置位置 | 对话线程中应可见的工具示例 |
|--------|----------|---------------------------|
| chrome-devtools | `.cursor/mcp.json` | 页面列表、console、network、截图 |
| playwright | `.cursor/mcp.json` | `browser_navigate`、`browser_snapshot` 等 |
| wechat-chrome-session | `.cursor/mcp.json` | `list_pages`、`select_page` 等 |
| stitch | `.cursor/mcp.json`（Remote MCP） | 设计 screen / 导出相关工具 |
| filesystem | `.cursor/mcp.json` | 读写 `${workspaceFolder}` 内文件 |
| context7 | `.cursor/mcp.json` | 库文档查询 |
| github | `.cursor/mcp.json` | 仓库 / PR / issue 操作 |

---

## 参考

- [`docs/cursor_browser_ui_runbook.md`](cursor_browser_ui_runbook.md)
- [`docs/agent_skills/mcp_usage_skill.md`](agent_skills/mcp_usage_skill.md)
- [`.cursor/rules/no-multitask-for-browser.mdc`](../.cursor/rules/no-multitask-for-browser.mdc)
- [`docs/mcp/WORKSPACE_MCP_SERVERS.md`](mcp/WORKSPACE_MCP_SERVERS.md)
