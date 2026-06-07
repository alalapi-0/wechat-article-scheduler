# Cursor UI 实现 Prompt 模板

复制下方 **Prompt 正文** 到 **新建的普通前台 Agent 对话**（禁用 Multitask），用于下一轮 UI 推进。

前置条件：

- Cursor Settings → Tools & MCP 中 chrome-devtools、playwright、stitch、filesystem 等已 ready；
- 已完全退出并重启 Cursor（若刚批准 MCP）；
- 当前对话中能看到对应 MCP 原生工具。

---

## Prompt 正文（复制从这里开始）

```markdown
请在本仓库执行一轮 **UI 实现与浏览器验证**（不是业务功能开发）。

## 硬性约束

1. 使用 **普通前台 Agent**；**禁止 Multitask** 或后台子 Agent。
2. 任务开始前 **检查当前对话线程** 是否暴露以下 MCP 原生工具：
   - stitch（设计输入）
   - chrome-devtools 或 playwright（页面检查）
   - filesystem（文件真值）
   若缺失任一必需工具，输出 `BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY` 并停止，不要假装执行。
3. **每轮只改一个主要 UI 切片**，不改变业务逻辑（预检、排期、队列、上传等核心流程必须保持可用）。
4. Stitch 导出 **只能** 作为设计输入，保存到 `docs/design/stitch/`；**不得**无审查覆盖业务代码。
5. 微信已登录后台任务 **不在本轮**（若涉及 mp.weixin.qq.com，只用 wechat-chrome-session，与本 Prompt 的本地 Web UI 任务隔离）。

## 阅读顺序

1. README.md
2. AGENTS.md（Cursor Browser UI Workflow 章节）
3. docs/rounds.md 或 docs/roadmap_converged.md（当前 UI 相关轮次）
4. docs/design/DESIGN.md
5. docs/design/stitch/UI_TASKS.md
6. docs/cursor_browser_ui_runbook.md

## 执行流程

1. 运行 `npm run check:cursor-mcp`（辅助；仍以当前线程工具为准）。
2. 启动 Web：`python -m wechat_article_scheduler.cli serve` → http://127.0.0.1:8080/
3. 用 chrome-devtools 或 playwright 打开目标页面。
4. **Before**：截图 + 检查 console + 检查 network，保存到 `docs/reports/ui_review/`。
5. 读取 Stitch 设计或调用 Stitch MCP 获取设计输入。
6. **选定一个 UI 改造切片**（例如：空状态、队列表格、详情页某一区块）。
7. 修改代码（FastAPI + 原生 HTML/CSS/JS）。
8. 重新打开页面。
9. **After**：截图 + console + network 检查。
10. 响应式 spot-check：desktop 1280 / tablet 768 / mobile 375。
11. 运行测试：`python -m pytest` 或 `python scripts/agent_gate.py gate`。
12. 更新必要文档（设计评审记录等）。
13. 用户明确要求时：`git diff` 确认无密钥后 commit；push 需用户单独授权。

## 输出要求

- 说明选择了哪个 UI 切片及原因
- Before / after 截图路径
- console / network 检查结果摘要
- 测试命令与结果
- 若工具缺失：BLOCKED 原因与用户恢复步骤

## 参考规则

- .cursor/rules/cursor-browser-ui.mdc
- .cursor/rules/no-multitask-for-browser.mdc
- .cursor/skills/browser-debug-check/SKILL.md
```

## Prompt 正文（复制到这里结束）

---

## 变体：仅浏览器回归（不改代码）

若只需验证现有 UI，将「执行流程」第 6–7 步替换为：

> 不修改代码；走完整用户路径并记录 console / network / 截图。

## 变体：Stitch 设计轮（不实现）

若只需生成设计输入，将约束改为：

> 只调用 Stitch MCP，输出保存到 `docs/design/stitch/exports/` 与 `screenshots/`；不修改 `src/`。

---

## 相关文档

- [`docs/cursor_browser_ui_runbook.md`](../cursor_browser_ui_runbook.md)
- [`docs/cursor_tool_registry_check.md`](../cursor_tool_registry_check.md)
- [`docs/design/stitch/PROMPT_TEMPLATES.md`](../design/stitch/PROMPT_TEMPLATES.md)
