# Agent Layer Audit

Date: 2026-06-09  
Round: layer2-tool-aware-bootstrap

## 审计结论

| Layer | Status | File | Notes |
|-------|--------|------|-------|
| Read First | added | AGENTS.md (补强) | 兼容 Cursor + Codex |
| Machine config | added | agent_layer.yaml | v2 |
| Tool manifest | added | agent_tools.yaml | 基于探针 |
| Tool inventory | added | docs/TOOL_INVENTORY.md | |
| Tool policy | added | docs/TOOL_USAGE_POLICY.md | |
| Search policy | added | docs/SEARCH_POLICY.md | |
| Research notes | added | docs/RESEARCH_NOTES.md | 4 queries |
| Runbook | added | docs/AGENT_RUNBOOK.md | 与既有 runbooks 并存 |
| Roadmap | added | docs/AGENT_ROADMAP.md | 30 轮 |
| Reporting | added | docs/AGENT_REPORTING.md | |
| Safety | added | docs/AGENT_SAFETY.md | |
| Cost | added | docs/COST_CONTROL.md | |
| Codex | added | docs/CODEX_USAGE.md, CODEX_HANDOFF.md | |
| Prompts | added | docs/PROMPTS.md | |
| User view | added | docs/USER_VIEW_TESTING.md | |
| Schema | added | schemas/agent_round_report.schema.json | |
| Tool probe | added | scripts/tool_probe.py | |
| Layer gate | added | scripts/agent_layer_gate.py | |
| User view script | added | scripts/user_view_test.py | |
| Cursor rules | added | .cursor/rules/agent-layer.mdc 等 | |
| Legacy gate | kept | scripts/agent_gate.py | 未删除 |
| Legacy rounds | kept | docs/rounds.md | 未删除 |

## 未改动（故意）

- `.env` / 凭证
- 业务大功能
- 既有 MCP 配置语义
- `docs/rounds.md` round 注册表

## 风险

- MCP `callable_now` 需每线程重验
- 仓库有大量未提交改动（非本轮回滚）
- Codex 可用性 unknown
