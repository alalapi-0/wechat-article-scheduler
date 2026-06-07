# Stitch UI Implementation Round

## 1. 当前项目类型判断

本项目是个人本地微信公众号草稿箱辅助工作台，不是多平台 SaaS、营销首页或团队审批系统。当前技术栈为 `FastAPI + 原生 HTML/CSS/JS + SQLite`，Web 工作台入口由 `python3 -m wechat_article_scheduler.cli serve` 启动，默认 `WECHAT_MODE=mock`，普通视图优先回答“现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办”。

本轮开始前已检查：

- `README.md`、`AGENTS.md`、治理文件、路线图、设计文档、测试文档和主 Web 模板。
- `package.json` 中存在 `npm run check:mcp` 与 `npm run check:stitch`。
- `.cursor/mcp.json` 包含 `stitch` remote MCP；`.env.example` 包含占位 `STITCH_API_KEY`。
- `ROADMAP.md`、`TODO.md`、`NEXT_STEPS.md`、`agent.md`、`app/`、`frontend/`、`backend/`、`web/`、`playwright.config.*` 在当前仓库根不存在；本轮以 `docs/rounds.md`、`docs/roadmap_converged.md`、`governance/round_state.yaml` 和 `src/wechat_article_scheduler/web/` 为准。
- 用户指定的 `reference_lab/10_ui_design_refs/reports/` 报告路径在当前工作区不存在；已按缺失记录处理，未阻塞当前 UI 轮。

## 2. 本轮 UI 改造切片

本轮只选择一个主切片：主工作台首页 Dashboard 的“安全状态 + 下一步 + 三步主流程”核心区域。

选择原因：

- 当前首页已经具备作品库、队列、草稿、事件等功能，但首屏“安全模式、下一步、主按钮”分散在顶部状态条、概览和右侧发布计划之间。
- 这是普通用户最先看到、最影响判断是否安全的核心区域。
- 可通过现有 `/api/overview`、`/api/status`、`/api/queue-summary`、`/api/drafts-summary` 数据实现，不需要改后端业务逻辑。

范围：

- 新增首屏 `safety-dashboard` 区块，展示 mock / real / draft-only 状态、到点执行状态、下一步 headline、主操作按钮、四个关键计数和三步流程。
- 让右侧“主操作”三步卡片与当前推荐动作同步高亮。
- 保留原有作品库、队列、草稿、事件、上传、排期、执行、预览、导出等逻辑。

非目标：

- 不引入 React/Vue 或大型 UI 框架。
- 不重构后端。
- 不把 Stitch HTML 直接塞进业务模板。
- 不恢复已移除的内容审核概念。

## 3. Stitch 使用计划

计划采用 `docs/design/stitch/UI_TASKS.md` 的“主控制台 Dashboard”任务和 `docs/design/stitch/PROMPT_TEMPLATES.md` 的 Dashboard prompt：

- Desktop-first 1280x900。
- 顶部安全状态和主内容区。
- 三步流程：找文章 -> 安排时间 -> 执行到点文章。
- 普通信息优先，高级信息折叠。
- 明确 mock / dry-run / real_api / 草稿-only。
- 原生 HTML/CSS/JS 可落地。

实际执行结果：

- `npm run check:mcp`：PASS。
- `npm run check:stitch`：PASS。
- 当前环境 `STITCH_API_KEY` 已设置，但可用 MCP 文件系统中没有直接列出的 `stitch` 工具 descriptor，无法按要求先读 descriptor 后调用 Stitch tool。
- 因此本轮使用 fallback：基于 `docs/design/stitch/PROMPT_TEMPLATES.md`、`UI_TASKS.md`、`DESIGN.md` 和现有 UI 报告约束手工形成设计输入，并保存到：
  - `docs/design/stitch/reviews/stitch_round_design_notes.md`
  - `docs/design/stitch/reviews/stitch_round_design_tokens.md`

## 4. 实现计划

1. 在 `src/wechat_article_scheduler/web/admin_template.html` 中新增首屏 `safety-dashboard`。
2. 新增轻量 CSS token 和响应式规则，保持当前克制、浅色、工作台风格。
3. 复用现有 `refreshAll()` 获取的 `ov`、`dsum`、`publish_preflight`、`workbench` 数据渲染 Dashboard。
4. 新增 `renderDashboard()`、`dashboardMode()`、`dashboardPrimaryConfig()` 和三步高亮映射。
5. 主按钮复用现有 `onScan()`、`onPlan()`、`onRun()`、`refreshAll()` 或导航逻辑，不新增危险操作。
6. 补充静态 HTML 回归测试。
7. 启动本地服务并执行真实浏览器检查：桌面、平板、窄屏，console，network，主按钮。

## 5. 验收标准与完成结果

验收标准：

- 首页能打开且不白屏。
- 首屏可见“安全状态与下一步”区域。
- mock / real / draft-only 状态清楚，不把 mock 说成真实发布。
- 主按钮可点击，复用已有安全门控。
- 作品库空状态、队列空状态、草稿区、主操作和事件区仍可见。
- 1280、768、375 宽度不出现整页横向溢出。
- console 无严重 error；network 核心 API 无失败。
- `npm run check:mcp`、`npm run check:stitch`、相关 pytest 和 gate 通过或记录环境问题。
- 提交前检查无 `.env`、真实 API key、token、cookie 或大截图进入提交。

完成结果：

- 已在首页落地首屏 Dashboard 切片。
- 已补充静态测试断言。
- 已记录 Stitch fallback 设计说明和 tokens。
- 浏览器检查已使用 Playwright MCP 打开 `http://127.0.0.1:8080/` 验证：桌面、768、375 宽度均无整页横向溢出；console 无 warning/error；核心 `/api/*` 请求 200；Dashboard 主按钮在 mock 模式下成功走通 `run-once` 并刷新下一步状态。
- 测试结果：`npm run check:mcp` PASS；`npm run check:stitch` PASS；`.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_console_mvp.py tests/test_ui_e2e.py -q` PASS；`.venv/bin/python scripts/agent_gate.py gate` PASS。
- 已修复一次 E2E 暴露的问题：Dashboard 主按钮文案避免与原「扫描本地收件箱」按钮重名，防止 Playwright 严格定位冲突。
- commit 与 push 结果见父任务最终报告。
