# wechat-article-scheduler

个人本地微信公众号草稿箱辅助工作台。

当前项目不是多平台发布器，不是商业 SaaS，不是团队协作后台，也不内置完整 Browser Agent。阶段一只优先打通微信公众号文章草稿箱辅助闭环；知乎、豆瓣、小红书、视频号、Bilibili、抖音、快手、网易云音乐等平台全部属于后期 backlog。

## 当前第一阶段目标

阶段一目标是把本地文章稳定送入微信公众号草稿箱，并在用户显式确认后才允许正式发布。

核心能力方向：

- 本地文章导入、去重、排期
- Markdown / TXT / HTML 到微信公众号正文
- 摘要 digest 120 字限制
- 封面上传、封面绑定和后续裁剪预览
- 微信公众号草稿创建和后续草稿更新
- 本地 scheduler 和失败重试
- Web 控制台：文章列表、详情、预览、草稿、队列、设置、事件日志
- 人工确认和可选正式发布
- 必要时导出外部 Browser Agent 任务包，交给 Hermes / Cursor Agent / Playwright MCP / Browser Use 或用户手动处理后台字段

## 已实现能力

- CLI 闭环：`scan` / `plan` / `run-once` / `scheduler`
- SQLite 状态记录：`articles`、`publish_jobs`、`wechat_drafts`、`events`
- 默认 `WECHAT_MODE=mock`，不联网；显式切到 `WECHAT_MODE=real` 后进入真实 API 测试模式
- 微信公众号 real adapter：token、封面素材上传、`draft/add`、受控 `freepublish/submit`
- `WECHAT_ENABLE_PUBLISH=false` 时只创建草稿，不正式发布
- 摘要 120 字兜底截断和 warning 事件
- Web 工作台基础能力：上传、文章列表、排期、预览、队列、预检、事件
- 外部 Browser Agent 任务包骨架：`outbox/wechat_agent_tasks/job-xxxxxx/`
- **里程碑（round_108–121）**：微信 P0 工作台抛光——预检门控、扫描/上传反馈、localStorage 持久化（高级信息/合集/队列 Tab/区块 hash）、详情返回上下文与深链 `#queue`
- 真实微信公众号草稿创建已通过本地验证

## 尚未完成

- 微信草稿更新能力
- 更稳定的 Markdown 到微信公众号 HTML 排版
- 更接近公众号效果的发布前预览
- 封面裁剪与方形/横向双比例预览
- 多合集/多专栏排期规则收口
- scheduler 常驻运行手册与稳定化
- API 不支持字段的外部 Agent proof 回填完善
- 完整微信公众号闭环验收

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/rules.example.yaml config/rules.yaml
python3 -m wechat_article_scheduler.cli init-db
```

启动 Web 工作台：

```bash
python3 -m wechat_article_scheduler.cli serve
```

打开 `http://127.0.0.1:8080/`。

纯 CLI：

```bash
python3 -m wechat_article_scheduler.cli scan
python3 -m wechat_article_scheduler.cli plan
python3 -m wechat_article_scheduler.cli run-once
```

仓库已纳入 `articles/imported/` 与 `articles/published/` 下的章节样稿，供 scan/plan 测试使用。不要提交 `.env` 或运行时数据库。

## 运行模式

| 模式 | 行为 |
|---|---|
| `WECHAT_MODE=mock` | 默认模式，不联网，生成 mock 草稿/发布结果 |
| `WECHAT_MODE=real` | 真实 API 测试模式；`real_api_check` 与到点执行会联网 |
| `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH=false` | 推荐：草稿-only，只创建真实微信草稿，不提交正式发布 |
| `WECHAT_MODE=real` + 任务级正式发布 | 到点时允许调用 `freepublish/submit` |

默认不联网；`WECHAT_MODE=real` 本身就是显式真实 API 测试开关。需要只测草稿箱时，设置 `WECHAT_ENABLE_PUBLISH=false`。任务级“仅草稿”仍不会触发正式发布。

当前定时发布实现是**本地 scheduler 到点调用 API**：先创建草稿，再在到点时按任务设置调用 `freepublish/submit`。它还不是“把定时时间写进微信后台草稿箱”的能力；如果微信官方 API 不支持该字段，后续应走外部 Browser Agent 任务包 + 人工确认路线。

## 外部 Browser Agent 协作模式

本项目不内置 Browser Agent，不集成 Hermes SDK、Browser Use SDK 或 Playwright MCP 服务，也不需要配置大模型即可使用 API 草稿功能。

后台浏览器操作交给外部成熟工具完成。本项目只生成标准化任务包：

```text
outbox/wechat_agent_tasks/job-000001/
  task.json
  browser_agent_prompt.md
  checklist.md
  article_preview.html
  article_source.md
  metadata.json
  proof_template.md
```

生成单个任务包：

```bash
python3 -m wechat_article_scheduler.cli export-agent-task --job-id 1
```

批量导出已创建草稿的任务：

```bash
python3 -m wechat_article_scheduler.cli export-agent-tasks --status draft_created
```

用户可以把 `browser_agent_prompt.md` 发给 Hermes / Cursor Agent / Playwright MCP / Browser Use。外部 Agent 只负责打开微信公众号后台、定位草稿、核对字段、辅助填写允许的非最终设置、截图或生成报告，并且必须停在人类确认阶段。

任务包不包含任何密钥；不会写入 access token、AppSecret、公众号后台 cookie、微信账号密码或 LLM API Key。外部 Agent 不能默认点击最终发布。任务完成后，用户需要将截图、后台状态描述、发布链接或草稿确认结果作为 proof 回填或记录到本项目。

当前项目的核心能力仍然是微信公众号 API 草稿创建和本地任务管理。

## 真实 API 验证

样本见 `fixtures/real_api_samples/`；报告写入 `reports/real_api_runs/`。

只验证 token、封面上传和草稿创建，不提交正式发布（推荐 `WECHAT_ENABLE_PUBLISH=false`）：

```bash
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python3 scripts/real_api_check.py --samples 3
```

无本地凭证或仍为 mock 时，可 dry-run 并跳过硬失败（Agent 门控用）：

```bash
python3 scripts/real_api_check.py --dry-run --skip-if-blocked
```

验证正式发布接口，会调用 `freepublish/submit`（慎用）：

```bash
WECHAT_MODE=real python3 scripts/real_api_check.py --samples 1 --publish
```

Auto-Approved 端到端（真实草稿 + auto_approved 元数据 + 可选 scan/run-once 下游），报告见 `reports/auto_approve_pipeline/`：

```bash
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python3 scripts/auto_approve_pipeline.py --round 1 --samples 3
```

无凭证时：

```bash
python3 scripts/auto_approve_pipeline.py --round 1 --dry-run --skip-downstream --skip-if-blocked
```

本地定时发布测试建议使用 Web 批量发布设置或 CLI 排期：把任务设为“正式发布”，并让本地 scheduler 到点执行。当前代码还没有把定时时间直接写入微信后台草稿箱。

## Scheduler 常驻运行

个人本地长期跑调度（**默认 mock**，不依赖浏览器开着）：

```bash
# 健康检查
python3 -m wechat_article_scheduler.cli scheduler-health

# 前台轮询（Ctrl+C 停止）
python3 -m wechat_article_scheduler.cli scheduler-daemon

# 或包装脚本（供 launchd / systemd 调用）
bash scripts/run_scheduler_daemon.sh
```

- **运行手册**：`docs/scheduler_runbook.md`（tmux、launchd、systemd、cron、日志、故障处理）
- **稳定化说明**：`docs/scheduler_stability.md`（claim、锁、退避重试）
- **示例文件**：`deploy/examples/scheduler/`

真实 API 测试请先在 `.env` 设 `WECHAT_MODE=real`；草稿-only 建议 `WECHAT_ENABLE_PUBLISH=false`。勿同时开常驻 `scheduler` 与 cron `run-once`。

## CLI 命令

| 命令 | 说明 |
|---|---|
| `init-db` | 初始化 SQLite |
| `scan` | 扫描 inbox、去重、入库 |
| `plan` | 生成 `publish_jobs` |
| `run-once` | 执行到期任务 |
| `scheduler` | 后台轮询调度 |
| `scheduler-daemon` | 常驻调度（同 scheduler，见运行手册） |
| `scheduler-health` | 队列/锁/卡住任务健康检查 |
| `update-draft --article-id N` | 更新已有微信草稿（需先有草稿记录） |
| `export-agent-task --job-id N` | 为指定发布任务生成外部 Browser Agent 任务包 |
| `export-agent-tasks --status draft_created` | 批量生成外部 Browser Agent 任务包 |
| `reject --article-id N` | 从发布流程移除某篇文章 |
| `retry-failed` | 重置失败任务为待执行 |
| `events --limit N` | 查看审计事件 |
| `serve` | 启动本地 FastAPI 工作台 |

## 文档入口

- 当前路线收敛审计：`docs/route_convergence_audit.md`
- 产品愿景：`docs/product_vision.md`
- 微信公众号优先架构：`docs/architecture.md`
- 收敛路线图：`docs/roadmap_converged.md`
- Scheduler 常驻手册：`docs/scheduler_runbook.md`
- 平台优先级：`docs/platform_priority.md`
- 微信 browser_assist 策略：`docs/wechat_browser_assist_strategy.md`
- 外部 Browser Agent 策略：`docs/external_browser_agent_strategy.md`
- 外部 Agent 任务包设计：`docs/external_agent_task_package_design.md`
- 外部 Agent 集成指南：`docs/external_agent_integration_guide.md`
- 外部 Agent 安全策略：`docs/external_agent_safety_policy.md`
- 微信草稿流程：`docs/wechat_draft_workflow.md`
- 发布状态机：`docs/state_machine.md`
- 历史权威轮次记录：`docs/rounds.md`
- 长期 backlog：`docs/backlog/`

## 外部 Agent 安全边界

外部 Agent 只作为微信公众号路线的本地自用后备方案，用于 API 无法覆盖字段时辅助打开后台、定位草稿、填写字段、截图和停在人机确认。

它不能：

- 绕过登录、验证码或平台风控
- 保存平台密码
- 保存公众号后台 cookie
- 默认点击最终发布
- 批量灌水
- 伪装成官方 API 能力
- 读取或写入本项目密钥

## 多平台扩展

多平台扩展属于未来 backlog：

- P1：知乎、豆瓣、WordPress / 个人博客
- P2：小红书、微信视频号、Bilibili、抖音、快手
- P3：网易云音乐、播客平台

阶段一完成前，不开发其他平台。

## MCP 配置检查

本项目在 Cursor 中要求启用 `chrome-devtools`、`context7`、`filesystem`、`github`、`playwright`。检查命令：

```bash
npm run check:mcp
```

GitHub token 必须通过环境变量注入，不得写入仓库或 `.cursor/mcp.json`。

## Stitch Design MCP

[Google Stitch](https://stitch.withgoogle.com/) 在本项目中负责 UI 设计输入：生成工作台、审核台、预览页和 debug 页面方案，以及 screen、variants、截图和 HTML。它不替代主开发 Agent，也不改变微信公众号 P0 业务边界。

本仓库使用 Remote MCP。先在本机设置 key：

```bash
export STITCH_API_KEY="your-local-key"
npm run check:mcp
npm run check:stitch
```

然后重启 Cursor 或 Reload Window，在 Tools & MCP 确认 `stitch` enabled。设计任务从 `docs/design/DESIGN.md` 和 `docs/design/stitch/` 开始；HTML、截图、prompt 和评审分别保存到该目录下的 `exports/`、`screenshots/`、`prompts/`、`reviews/`。

协作分工：Stitch 提供设计输入，Cursor/实现 Agent 按当前 `FastAPI + 原生 HTML/CSS/JS` 技术栈落地，Codex 可执行用户视角与浏览器测试。Stitch 导出代码不得无审查覆盖业务代码；实现后必须用 Playwright 或 chrome-devtools 检查页面、console、network 和核心流程。

安全要求：

- 不提交 `.env`，不把 `STITCH_API_KEY` 的真实值写进代码、文档、日志或 `.cursor/mcp.json`。
- 静态检查通过但 MCP 未连接时，先确认 Cursor 进程能读取环境变量，再重载窗口。
- 无 key、认证失败或服务不可用时，记录原因并用文档模板继续，不把失败结果描述为已生成。

详细设置与常见问题见 [`docs/design/stitch/STITCH_MCP_SETUP.md`](docs/design/stitch/STITCH_MCP_SETUP.md)。
