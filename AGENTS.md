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
- `context7`
- `filesystem`
- `github`
- `playwright`

用途：

- **chrome-devtools**：浏览器调试、console、network、页面状态检查。
- **context7**：查询第三方库和框架文档。
- **filesystem**：安全读取和检查当前项目文件（仅 `${workspaceFolder}`）。
- **github**：仓库、提交、分支、issue、PR 等相关操作。
- **playwright**：浏览器自动化、页面操作、E2E 检查。

自动推进轮开始前，Agent 必须确认上述 MCP 已在 Cursor 中加载；并运行 `node scripts/check_mcp_config.js` 或 `npm run check:mcp`（亦可 `python scripts/check_mcp_config.py`）。修改 `mcp.json` 后通常需 **重启 Cursor** 或重新加载窗口。

若某个 MCP 不可用，Agent 需记录原因，并按 `docs/agent_skills/mcp_usage_skill.md` 使用可用替代方案继续推进；不因单个非阻塞 MCP 停止整轮。

涉及页面、审核台、生成结果、预览、发布流程的任务，必须使用 **chrome-devtools** 或 **playwright** 进行真实浏览器检查（页面 + console + network + 核心流程），不得仅凭代码或截图判断成功。

- GitHub 操作前必须 `git diff`；token 通过环境变量 `GITHUB_TOKEN`（或 `GITHUB_PERSONAL_ACCESS_TOKEN`）注入，禁止写入仓库或 MCP 配置。
- 若缺少第三方 token/API Key 且任务可 mock/dry-run，不要卡死整体流程；仅当 token 为当前子任务唯一阻塞时才暂停该子任务。

## 常用命令

```bash
npm run check:mcp                           # MCP 配置与安全检查（Node）
python scripts/check_mcp_config.py          # MCP 配置与安全检查（Python）
python -m wechat_article_scheduler.cli init-db
python -m wechat_article_scheduler.cli scan
python -m wechat_article_scheduler.cli plan
python -m wechat_article_scheduler.cli run-once
python -m pytest
```
