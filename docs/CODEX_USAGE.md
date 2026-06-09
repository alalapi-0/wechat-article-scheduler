# Codex Usage

## Codex 适合

- 大范围重构
- 长程推进（多文件）
- 代码审查 / PR review
- 测试生成
- worktree 并行任务
- 难问题集中攻关

## Cursor 适合（主力）

- 本地快速修复
- UI 调试与浏览器用户视角
- MCP 工具联动
- 小轮次实现
- 文档与规则落地
- tool_probe / gate / report

## Codex 启动前必读

1. `AGENTS.md`
2. `agent_layer.yaml`
3. `agent_tools.yaml`
4. `docs/TOOL_USAGE_POLICY.md`
5. `docs/AGENT_RUNBOOK.md`
6. `reports/latest-agent-report.json`
7. `docs/CODEX_HANDOFF.md`（若由 Cursor 交接）

## 任务格式

- plan first
- small scope（one round only）
- no real API / no real publish
- run gate
- generate report

## 额度有限策略

- 仅高价值任务
- 不做文档润色、小修小补
- 用前由 Cursor 生成 `docs/CODEX_HANDOFF.md`
- MCP 配置在 `~/.codex/config.toml`（TOML，非 JSON）

## 配置提示

```toml
# ~/.codex/config.toml 示例
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--isolated"]
enabled = true
```
