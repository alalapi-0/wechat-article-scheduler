# Research Notes

Date: 2026-06-09  
Agent: Cursor  
Search capability: available

## Query 1 — Cursor Agent 能力与 AGENTS.md

- Query: Cursor IDE Agent Rules Skills AGENTS.md MCP 2026
- Source type: official docs
- Key finding: Cursor 通过 `.cursor/rules/`（Rules）、`SKILL.md`（Skills）、`AGENTS.md`（项目级说明）与 `mcp.json`（MCP）分层定制 Agent；CLI 工具（gh、docker 等）可直接由 Agent 调用。
- Relevance to this repo: 既有 `.cursor/rules/` 与 `AGENTS.md` 正确；Layer 2.0 应交叉引用而非重复。
- Risk / uncertainty: Cloud Agent / Hooks 细节需以 cursor.com/docs 最新页为准。
- Action to encode into repo: 补强 `AGENTS.md` Read First；新增 Layer 2.0 Cursor rules。

## Query 2 — Codex CLI 与 AGENTS.md

- Query: OpenAI Codex CLI AGENTS.md MCP web search 2026
- Source type: official docs
- Key finding: Codex 读取 `AGENTS.md`（与 CLAUDE.md 类似），支持 MCP（`~/.codex/config.toml`）、Web Search、Subagents、Skills；默认需审批危险操作。
- Relevance to this repo: 同一 `AGENTS.md` 可服务 Cursor 与 Codex；handoff 用 `docs/CODEX_HANDOFF.md`。
- Risk / uncertainty: 本环境 `CODEX_AVAILABLE: unknown`。
- Action to encode into repo: `docs/CODEX_USAGE.md`、`docs/CODEX_HANDOFF.md`。

## Query 3 — 微信公众平台草稿 API

- Query: 微信公众号 draft add 官方文档
- Source type: official docs
- Key finding: `POST .../cgi-bin/draft/add`；`digest` 最长 128 字；`title` ≤32 字；`content` 支持 HTML、过滤 JS、外部图片 URL 被过滤；草稿群发/发布后从草稿箱移除。
- Relevance to this repo: 与项目 digest 120 字兜底、draft-only 策略一致；定时发布不能靠 API 写入微信后台。
- Risk / uncertainty: 2025-12 字段描述有更新，实现须对照 `docs/wechat_capability_matrix.md`。
- Action to encode into repo: 保持 mock 默认；真实 API 仅显式开关。

## Query 4 — FastAPI 最新文档

- Query: FastAPI documentation 2026
- Source type: official docs
- Key finding: 文档站 https://fastapi.tiangolo.com/ 不版本化，跟踪最新版（PyPI 0.136.x）；本项目 Web 工作台基于 FastAPI + 原生 HTML。
- Relevance to this repo: `requirements.txt` 声明 `fastapi>=0.110`；升级前查 release-notes。
- Risk / uncertainty: 无。
- Action to encode into repo: context7 / web_search 作为 API 不确定时的查阅路径。
