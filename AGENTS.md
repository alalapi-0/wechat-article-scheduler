# AGENTS.md

微信公众号文章本地调度器。默认 **WECHAT_MODE=mock**，不调用真实微信 API。

## 路线图单一真相来源

| 用途 | 文件 |
|------|------|
| 人类可读路线图（权威） | `docs/rounds.md`（Round 0–53） |
| 机器可读轮次注册表 | `scripts/agent_gate.py` 的 `ROUND_ORDER` / `ROUND_META` |
| 当前轮次运行状态 | `governance/round_state.yaml` |

修改路线图时：**先改 `docs/rounds.md`，再同步 `agent_gate.py` 与 `tests/test_agent_gate.py`**。`articles/imported/` 与 `articles/published/` 下的章节文稿已纳入仓库，供 scan/plan 测试使用。

Web 控制台路线图原则：**普通用户视图优先 + Desktop-first local workbench**。普通视图只回答“现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办”；数据库路径、原始 JSON、内部字段、调试统计默认进入高级信息开关。优先电脑浏览器的信息密度、任务队列表格、文章列表、事件日志、左侧导航/顶部状态；手机/平板只做响应式兼容（不横向溢出、关键按钮可点、页面可读），不得作为默认布局目标。

## 阅读顺序

1. `governance/repo_protocol_standard.yaml`
2. `project.yaml`
3. `governance/agent_policy.yaml`
4. `governance/round_state.yaml`
5. `docs/rounds.md`
6. `README.md`

## 自主推进

```bash
python scripts/agent_gate.py status          # 当前轮、验收项、next_actions
python scripts/agent_gate.py gate            # pytest + 轮次冒烟（exit 0 可继续）
python scripts/agent_gate.py advance --commit  # 通过后推进 round_state；可选提交
```

Agent 循环：`status` → 实现任务 → `gate` → `advance --commit`。默认**不** push；`--check-only` 等价于 `gate`。退出码：0=PASS，1=WARNING，2=BLOCKED（见 `governance/repo_protocol_standard.yaml`）。

## 禁止

- 读取/打印 `.env` 密钥
- 日志打印 token
- 未授权时 `WECHAT_MODE=real` 联网

## MCP Tools

当前项目要求启用以下 **Workspace MCP Servers**（配置见 `.cursor/mcp.json`）：

- `chrome-devtools`
- `wechat-chrome-session`
- `context7`
- `filesystem`
- `github`
- `playwright`
- `stitch`

用途：

- **chrome-devtools**：浏览器调试、console、network、页面状态检查。
- **wechat-chrome-session**：通过 `--autoConnect` 连接用户已批准的现有 Chrome；仅此 server 可用于复用公众号登录态。
- **context7**：查询第三方库和框架文档。
- **filesystem**：安全读取和检查当前项目文件（仅 `${workspaceFolder}`）。
- **github**：仓库、提交、分支、issue、PR 等相关操作。
- **playwright**：浏览器自动化、页面操作、E2E 检查。
- **stitch**：生成 UI 设计方案、screen、截图和 HTML，作为页面实现前的设计输入。

自动推进轮开始前，Agent 必须确认上述 MCP 已在 Cursor 中加载；并运行 `npm run check:mcp`，涉及设计任务时再运行 `npm run check:stitch`（亦可运行对应脚本）。修改 `mcp.json` 后通常需 **重启 Cursor** 或重新加载窗口。

若某个 MCP 不可用，Agent 需记录原因，并按 `docs/agent_skills/mcp_usage_skill.md` 使用可用替代方案继续推进；不因单个非阻塞 MCP 停止整轮。

涉及页面、审核台、生成结果、预览、发布流程的任务，必须使用 **chrome-devtools** 或 **playwright** 进行真实浏览器检查（页面 + console + network + 核心流程），不得仅凭代码或截图判断成功。

涉及用户已登录的微信公众号页面时，必须明确调用 **wechat-chrome-session** 的 `list_pages` / `select_page` 等工具。Cursor 内置 `browser_tabs`、普通 `chrome-devtools` 和 `playwright --isolated` 的页面列表不能作为接管现有 Chrome 的证明；若当前工具列表中没有 `wechat-chrome-session`，立即停止并要求 Reload Window 或在 **Settings -> Tools & MCP** 修复该 server。

真实公众号浏览器任务不得使用 Cursor **Multitask** 异步子 Agent；必须在启用了 MCP tools 的普通前台 Agent 对话中执行，避免子线程缺少 workspace MCP 工具注册。

- GitHub 操作前必须 `git diff`；token 通过环境变量 `GITHUB_TOKEN`（或 `GITHUB_PERSONAL_ACCESS_TOKEN`）注入，禁止写入仓库或 MCP 配置。
- 若缺少第三方 token/API Key 且任务可 mock/dry-run，不要卡死整体流程；仅当 token 为当前子任务唯一阻塞时才暂停该子任务。

## Stitch Design MCP

涉及 UI、新页面、审核台、预览页、管理后台或视觉检查页时，Agent 应先阅读：

- `docs/design/DESIGN.md`
- `docs/design/stitch/README.md`
- `docs/design/stitch/UI_TASKS.md`
- `docs/design/stitch/PROMPT_TEMPLATES.md`

若 `stitch` MCP 可用，可生成 UI 原型、screen、screenshot、HTML、`DESIGN.md` 和多方案 variants。导出物只保存到 `docs/design/stitch/exports/`、`screenshots/`、`reviews/`；不得无审查地覆盖业务代码。

实现前须把设计结果拆成符合当前 `FastAPI + 原生 HTML/CSS/JS` 技术栈的任务；实现后必须用 Playwright 或 chrome-devtools 检查页面、console、network 和核心流程。若 Stitch 不可用，记录原因，继续按设计模板推进，不阻塞可完成的工作。

## Cursor Browser UI Workflow

Cursor 做 UI 优化、Web 工作台改版或浏览器回归验证时，必须遵循以下规范（详见 [`docs/cursor_browser_ui_runbook.md`](docs/cursor_browser_ui_runbook.md) 与 [`docs/cursor_tool_registry_check.md`](docs/cursor_tool_registry_check.md)）：

1. **必须使用普通前台 Agent**；禁止 Multitask 或后台子 Agent 控制浏览器（见 `.cursor/rules/no-multitask-for-browser.mdc`）。
2. **每轮 UI 实现开始前**必须先检查真实页面，不得只凭代码判断完成。
3. **每轮 UI 实现必须做 before / after 浏览器检查**（截图 + console + network）。
4. **Stitch** 用作设计输入；导出物保存到 `docs/design/stitch/`，不得无审查覆盖业务代码。
5. **chrome-devtools** 用作页面调试（console、network、DOM、截图）。
6. **playwright** 用作 E2E 与稳定回归（多 viewport、重复路径）。
7. **filesystem** 用作文件真值检查（仅 `${workspaceFolder}`）。
8. **context7** 用作文档查询（FastAPI、Playwright 等）。
9. **github** 用作提交与远程状态（token 仅环境变量）。
10. **微信已登录页面**只允许 **wechat-chrome-session**；本地 Web 工作台（`http://127.0.0.1:8080/`）使用 chrome-devtools 或 playwright，不得混用。
11. **若当前对话线程缺少所需 MCP 工具**，输出 `BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY` 并停止；不要依赖 `cursor-agent mcp list` 或 Settings ready 状态假装可用。
12. UI 改造每轮只改一个主要切片；见 [`docs/prompts/CURSOR_UI_IMPLEMENTATION_PROMPT.md`](docs/prompts/CURSOR_UI_IMPLEMENTATION_PROMPT.md) 可直接复制使用的 Prompt 模板。

MCP CLI 辅助检查：`npm run check:cursor-mcp`（**不代表**当前对话线程已暴露工具）。

## 常用命令

```bash
npm run check:mcp                           # MCP 配置与安全检查（Node）
npm run check:cursor-mcp                    # Cursor CLI 层 MCP 状态（不代表当前对话线程）
npm run check:stitch                        # Stitch 配置、目录与密钥检查
python scripts/check_mcp_config.py          # MCP 配置与安全检查（Python）
python -m wechat_article_scheduler.cli init-db
python -m wechat_article_scheduler.cli scan
python -m wechat_article_scheduler.cli plan
python -m wechat_article_scheduler.cli run-once
python -m pytest
```
