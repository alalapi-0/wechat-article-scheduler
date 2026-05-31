# Agent 浏览器调试与验证闭环

本文档说明本仓库为 Cursor Agent 配置的浏览器调试、文档查询与验证门禁工具，以及后续 Agent 应如何执行验证闭环。

## 新增 MCP Server

配置位于 `.cursor/mcp.json`：

| MCP | 用途 |
|-----|------|
| **playwright** | 浏览器自动化：打开页面、点击、填表、截图、基本页面交互 |
| **chrome-devtools** | 深层 DevTools 调试：console 日志、network 请求、performance 分析 |
| **context7** | 查询第三方库/框架最新文档（prompt 中可写 `use context7`） |

### 如何在 Cursor 中确认 MCP 已启用

1. 打开 **Cursor Settings**
2. 进入 **Tools & MCP** → **MCP**
3. 确认 `playwright`、`chrome-devtools`、`context7` 为可用（绿色）状态
4. 若刚添加或修改 `.cursor/mcp.json`，**需要重启 Cursor** 后才会加载

首次使用时，MCP 会通过 `npx` 拉取对应包，需本机已安装 Node.js（建议 v18+）。

## Skill：browser-debug-check

路径：`.cursor/skills/browser-debug-check/SKILL.md`

涉及前端页面、Web 工作台、文件上传/删除、API 调用、内容预览等任务时，Agent 必须按该技能执行完整验证闭环，并输出结构化验证报告。

在 prompt 中可写：

```text
请调用 /browser-debug-check 技能完成本轮验证
```

## Rule：verification-gate

路径：`.cursor/rules/verification-gate.mdc`

该规则 `alwaysApply: true`，要求所有相关任务在完成后必须通过浏览器 + console/network + 测试/构建验证，禁止仅凭静态代码或截图判断完成。

## 本仓库特有的 Python 验证入口

本项目为 **Python + FastAPI** 本地工作台，**没有** `package.json`。验证请优先使用已有命令：

```bash
# 统一门禁（pytest + 轮次冒烟）
python scripts/agent_gate.py gate

# Web 服务（浏览器验证前需启动）
python -m wechat_article_scheduler.cli serve   # http://127.0.0.1:8080/

# Playwright UI 诊断脚本（需 pip install -e ".[dev]" && playwright install chromium）
python tools/browser_automation/ui_review.py --seed 5

# pytest 含 Web / Playwright E2E
python -m pytest tests/test_web_app.py tests/test_ui_e2e.py tests/test_ui_review.py -q
```

`pyproject.toml` 的 `[project.optional-dependencies] dev` 已声明 `playwright`；与 Cursor MCP 的 Playwright 是不同入口——MCP 用于 Agent 交互式调试，Python Playwright 用于自动化测试与 UI 基线截图。

## 修改后推荐验证顺序

1. 阅读 `AGENTS.md`、`README.md`、相关 `docs/`
2. 修改代码
3. 启动 `serve`（若涉及 Web UI）
4. 使用 **Playwright MCP** 或 **Chrome DevTools MCP** 打开目标页面，走至少一条真实用户路径
5. 检查 **console**（无 error）与 **network**（核心 API 无失败）
6. 运行 `python scripts/agent_gate.py gate` 或对应 pytest
7. 输出验证报告（见 Skill 输出格式）

## Prompt 示例

```text
请调用 /browser-debug-check 技能完成本轮验证
```

```text
use context7 查询 FastAPI 最新文档中 File Upload 的用法
```

## 安全注意事项

- **不要**让 MCP 打开真实支付后台或生产公众号后台
- **不要**用 MCP 操作生产账号或真实发布
- **不要**把 API Key、cookie、token、session 写入仓库或 MCP 配置
- 测试删除/移动文件时，仅使用测试目录或 mock 数据（默认 `WECHAT_MODE=mock`）
- **不要**读取或输出 `.env` 中的真实密钥

## 与 Node.js 前端项目的差异

若未来添加 `package.json` 与前端构建链，可补充 `agent:check` 脚本（`lint && test && build`）及 `tests/smoke.spec.ts`。当前阶段以 Python 门禁与 Playwright Python 测试为准。
