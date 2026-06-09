# MCP 文档

本目录说明 Cursor 工作区 MCP 的配置、用途、安全边界和降级方式。

**任务开始前请先读**：[`../runbooks/cursor_mcp_runbook.md`](../runbooks/cursor_mcp_runbook.md)

- [`../runbooks/`](../runbooks/)：MCP readiness Runbook、工具矩阵、浏览器上下文、故障排查
- [`WORKSPACE_MCP_SERVERS.md`](WORKSPACE_MCP_SERVERS.md)：当前 server 清单与任务映射。
- `../../.cursor/mcp.json`：实际配置。
- `../../scripts/check_mcp_config.js`：通用配置检查。
- `../../scripts/check_stitch_config.js`：Stitch、安全与设计目录检查。
- `../agent_skills/mcp_usage_skill.md`：Agent 操作细则。

修改 `.cursor/mcp.json` 后运行：

```bash
npm run check:mcp
npm run check:stitch
```

随后重启 Cursor 或 Reload Window，并在 Tools & MCP 确认 server enabled。静态脚本不能证明远端认证或浏览器连接已经成功。
