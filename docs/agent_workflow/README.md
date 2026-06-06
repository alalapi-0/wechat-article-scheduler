# Agent 工作流

本仓库 Agent 的最小闭环：

1. 按 `AGENTS.md` 阅读治理与当前状态。
2. 运行 `python3 scripts/agent_gate.py status`。
3. 运行 `npm run check:mcp`；UI 设计任务再运行 `npm run check:stitch`。
4. 只实现当前任务范围，默认 `WECHAT_MODE=mock`。
5. UI 任务先读 `docs/design/`，必要时用 Stitch 形成设计输入。
6. 页面实现后按 `docs/testing/BROWSER_TESTING.md` 验证。
7. 真实 API 按 `docs/testing/REAL_API_TESTING.md`，没有 key 时用 dry-run。
8. 运行 `python3 scripts/agent_gate.py gate`。
9. 提交前检查 `git status`、`git diff` 和密钥风险；默认不 push。

Stitch、浏览器和 GitHub MCP 都是辅助能力，不替代仓库治理、业务边界、人工确认和自动化门禁。
