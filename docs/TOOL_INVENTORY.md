# Tool Inventory

Date: 2026-06-09 (layer2-004 thread probe)  
Agent: Cursor  
Probe script: `python scripts/tool_probe.py`  
Machine report: `reports/tool_probe_report.json`

## 仓库类型

- **项目**：wechat-article-scheduler（Python CLI + FastAPI Web 工作台）
- **平台**：微信公众号草稿箱辅助（默认 mock，不联网）
- **主力 Agent**：Cursor（本地编辑 + MCP + 浏览器用户视角）

## CURSOR_CONFIG_VISIBILITY

`thread_verified`（layer2-004）— 配置层 `npm run check:mcp` PASS；**当前前台 Agent 线程** 已通过 `CallMcpTool` 安全探测确认 7 个 workspace MCP 均可调用。  
`npm run check:cursor-mcp` CLI 层仍显示 6 个 server `needs approval`，与线程注册表不一致 — **以线程实测为准**（见 `docs/cursor_tool_registry_check.md`）。

## A. 基础本地工具

| Tool | Available | Probe | Notes |
|------|-----------|-------|-------|
| shell | yes | `pwd` | 当前线程可用 |
| git | yes | `git status --short` | branch: main；大量未提交改动 |
| node | yes | v26.0.0 | |
| npm | yes | 11.12.1 | |
| pnpm | no | — | |
| yarn | no | — | |
| bun | no | — | |
| python3 | yes | 3.14.5 | |
| uv | yes | 0.11.19 | |
| pip | yes | 26.1.1 | |
| java | no | — | |
| mvn | no | — | |
| docker | no | — | |
| make | yes | GNU Make 3.81 | |
| ffmpeg | yes | 8.0.1 | 媒体流水线可用 |
| imagemagick | no | — | |
| playwright | yes | npx 1.60.0 | 另需 `playwright install chromium` |
| pytest | yes | 9.0.3 | |
| gh | yes | 2.92.0 | GitHub CLI |
| remote | yes | origin → github.com/alalapi-0/wechat-article-scheduler | 本轮不 push |

## B. Cursor 相关能力

| Item | Status | Path / Notes |
|------|--------|--------------|
| Project rules | configured | `.cursor/rules/*.mdc`（8 条既有 + Layer 2.0 补强） |
| MCP config | configured | `.cursor/mcp.json`（7 servers） |
| Skills | configured | `.cursor/skills/browser-debug-check/SKILL.md` |
| Browser / Design Mode | manual | 需在 Cursor UI 启用；见 `docs/cursor_browser_ui_runbook.md` |
| Cloud Agent | manual | 读取根目录 `AGENTS.md` |
| Subagents | manual | 浏览器任务禁止 Multitask（见 `no-multitask-for-browser.mdc`） |
| Hooks | unknown | 未在仓库发现 `.cursor/hooks.json` |
| Cursor CLI | partial | `npm run check:cursor-mcp`；不代表当前线程 |

## C. Codex 相关能力

| Item | Status |
|------|--------|
| CODEX_AVAILABLE | unknown（本环境未探测到 codex CLI） |
| AGENTS.md | yes — Codex 官方支持同级读取 |
| Codex MCP | manual — 配置于 `~/.codex/config.toml` 或 `.codex/config.toml` |
| Codex Skills | manual — `~/.agents/skills/` |
| Handoff | `docs/CODEX_HANDOFF.md` |

## D. MCP 工具（配置层）

配置检查：`npm run check:mcp` → **PASS**（7 servers）

| MCP | configured | callable_now | safe_probe | recommended_use | risks | fallback |
|-----|------------|--------------|------------|-----------------|-------|----------|
| chrome-devtools | true | **true** | `list_pages` | 本地 Web UI 调试 | isolated、非微信登录态 | playwright |
| wechat-chrome-session | true | **true** | `list_pages`（含 mp.weixin.qq.com） | 已登录公众号后台 | 禁止最终发布 | 外部任务包 |
| context7 | true | **true** | `resolve-library-id` FastAPI | FastAPI/Playwright 文档 | 需网络 | web_search |
| filesystem | true | **true** | thread registry（14 tools） | 工作区内文件 | 禁止越界路径 | Cursor Read |
| github | true | **true** | `search_repositories` | issue/PR | token 泄露 | gh CLI |
| playwright | true | **true** | `browser_tabs list` | E2E、多 viewport | isolated 无登录态 | pytest e2e |
| stitch | true | **true** | `list_projects` | UI 设计原型 | API key 仅环境变量 | 设计模板 |

**线程探测说明（layer2-004，2026-06-09）**：前台 Agent 线程暴露全部 7 个 workspace MCP（另含 `cursor-ide-browser`、`cursor-app-control`）。安全探测均成功；`wechat-chrome-session` 列出 7 个页面，含已登录 `mp.weixin.qq.com` 后台。  
layer2-001 线程曾 `callable_now: false`；本轮已更新为 `true`。每轮新对话须重新探测。

## E. Web Search

| Capability | Status |
|------------|--------|
| WebSearch | **available**（Cursor Agent 内置） |
| 策略 | 见 `docs/SEARCH_POLICY.md`；结论写入 `docs/RESEARCH_NOTES.md` |

## F. Browser / Playwright / 用户视角

| Capability | Status |
|------------|--------|
| Playwright（Python） | requirements.txt 已声明 |
| Playwright MCP | configured |
| 本地服务 | `python -m wechat_article_scheduler.cli serve` → :8080 |
| 用户视角脚本 | `python scripts/user_view_test.py` |
| pytest e2e | `tests/test_ui_e2e.py`, `tests/test_user_view_rounds_abcd.py` |
| 历史 UX 报告 | `docs/reports/ux_loop/` |

## G. GitHub

| Capability | Status |
|------------|--------|
| remote | configured |
| gh CLI | available |
| github MCP | configured, callable_now unknown |
| 本轮 push | **禁止**（协议默认） |
| 本轮 PR | **禁止**（协议默认） |

## H. Context7

- configured: true
- callable_now: **true**（layer2-004：`resolve-library-id` → `/fastapi/fastapi`）
- recommended_docs: FastAPI, Playwright, PyYAML, httpx

## 需人工确认项

1. **每轮新对话**重新执行线程 MCP 探测（CLI `check:cursor-mcp` 不等于线程可调用）
2. `GITHUB_TOKEN` / `STITCH_API_KEY` 是否仅在环境变量（禁止入库）
3. Codex CLI 是否在本机安装（`codex --version`）
4. 微信公众号真实 API 凭证仅在 `.env`（禁止 Agent 读取）
5. Multitask 子 Agent 通常不继承 workspace MCP — 浏览器任务须前台对话
