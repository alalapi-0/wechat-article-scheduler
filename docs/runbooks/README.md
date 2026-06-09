# Runbooks

本目录存放 **Cursor MCP 稳定运行** 与浏览器上下文相关的操作手册。

## 入口

**任务开始前请先读**：[`cursor_mcp_runbook.md`](cursor_mcp_runbook.md)

## 文档索引

| 文件 | 用途 |
|------|------|
| [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md) | MCP readiness 标准检查流程（主 Runbook） |
| [`mcp_tool_matrix.md`](mcp_tool_matrix.md) | 各 MCP 常用工具矩阵与边界 |
| [`browser_context_guide.md`](browser_context_guide.md) | isolated browser vs 已登录公众号后台 |
| [`mcp_troubleshooting.md`](mcp_troubleshooting.md) | 常见失败与恢复 |
| [`external_agent_browser_notes.md`](external_agent_browser_notes.md) | 外部 Browser Agent 与 MCP 分工 |
| [`check_mcp_readiness.md`](check_mcp_readiness.md) | 可读性检查清单（无脚本） |

## 相关（目录外）

- [`docs/mcp/WORKSPACE_MCP_SERVERS.md`](../mcp/WORKSPACE_MCP_SERVERS.md)
- [`docs/cursor_tool_registry_check.md`](../cursor_tool_registry_check.md)
- [`docs/wechat_chrome_session_runbook.md`](../wechat_chrome_session_runbook.md)
- [`docs/cursor_browser_ui_runbook.md`](../cursor_browser_ui_runbook.md)

## 基线

- **日期**：2026-06-07
- **配置检查**：`node scripts/check_mcp_config.js` PASS；`npm run check:stitch` PASS
- **已探测 MCP**：chrome-devtools、playwright、context7、filesystem、github、stitch（6 项线程探测成功）
