# 项目用户体验测试前置盘点报告

> 生成时间：2026-06-07  
> 盘点 Agent 任务：只读发现与本地验证，未修改业务代码、未调用真实微信发布/删除。

---

## 1. 本轮任务范围

本轮仅完成**项目发现、功能盘点、本地可运行性验证与界面巡检**，产出可复用的测试前置报告。明确**未做**：

- 业务代码重构、数据库结构修改、UI 改版、新功能实现
- 真实微信 API 发布/群发/远端删除（`WECHAT_MODE=real` 联网写操作）
- 微信公众号后台浏览器自动化（`wechat-chrome-session` 未用于本轮本地 Web 巡检）
- Git 提交、生产部署

允许且已执行：读文件、`.venv` 下 pytest/agent_gate、mock 模式启动 Web、cursor-ide-browser 本地页面巡检、创建本报告。

---

## 2. 仓库结构摘要

### 2.1 存在的关键路径

| 路径 | 状态 | 说明 |
|------|------|------|
| `README.md` | ✅ | 人类入口，快速开始与模式说明 |
| `AGENTS.md` | ✅ | Agent/MCP 工作流与命令 |
| `pyproject.toml` | ✅ | Python 包定义，pytest 配置 |
| `requirements.txt` | ✅ | 运行时 + dev 依赖 |
| `package.json` | ✅ | **仅 MCP 检查脚本**，非前端运行时 |
| `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` | ❌ | 无 Node 应用锁文件 |
| `.env.example` | ✅ | 环境变量模板 |
| `.env` | ✅（本地存在，未读取内容） | 用户本机配置 |
| `config/rules.example.yaml` | ✅ | 排期规则示例 |
| `docs/` | ✅ | 大量设计/路线图/运行手册 |
| `governance/` | ✅ | 轮次状态、Agent 策略 |
| `src/wechat_article_scheduler/` | ✅ | 主业务代码 |
| `tests/` | ✅ | 108 个 `test_*.py` |
| `migrations/` | ✅ | 14 个 SQL 迁移 |
| `scripts/` | ✅ | agent_gate、MCP 检查、real_api_check 等 |
| `articles/` | ✅ | imported/inbox/published 样稿 |
| `deploy/examples/` | ✅ | systemd/cron/plist 示例 |
| `Dockerfile` / `docker-compose*` | ❌ | 无容器化配置 |
| `.github/` | ❌ | 无 GitHub Actions |
| `prisma/` / `vite.config.*` / `next.config.*` | ❌ | 非 Node 全栈前端项目 |

### 2.2 项目形态判断

**类型**：Python CLI + FastAPI 本地 Web 工作台（个人本地工具，非 SaaS）。

**架构概览**：

```text
articles/inbox|imported  →  scan  →  SQLite(articles/jobs/drafts/events)
                              ↓
                         plan / schedule (Web 或 CLI)
                              ↓
                    run-once / scheduler (mock 或 real adapter)
                              ↓
              微信草稿 API (draft/add|update) + 外部 Agent 任务包 + 人工 proof
```

---

## 3. 项目基本信息判断

| 项 | 判断（附证据） |
|----|----------------|
| **项目名称** | `wechat-article-scheduler`（`pyproject.toml`、`project.yaml`） |
| **一句话定位** | 个人本地微信公众号草稿箱辅助工作台：导入、排期、到点创建/更新草稿，后台发布由用户人工完成（`README.md` L3–9） |
| **目标用户** | 个人公众号运营者；需批量管理本地 Markdown/TXT/HTML 文章、排期与草稿的技术型用户（`project.yaml` L10–11） |
| **主要解决问题** | 本地文章 → 微信草稿 API 的自动化准备；统一队列/事件/预检；导出外部 Browser Agent 任务包辅助后台核对（`README.md` L11–21） |
| **成熟度** | **E（已接近可用产品）**。证据：457 项 pytest 通过、agent_gate PASS、Web 工作台功能完整、真实草稿 API 已在文档与测试中验证；但仍有文档债、部分边界语义与多平台预研占位。 |
| **方向混乱/文档不一致** | **存在轻度不一致**：`docs/current_state_audit.md` 仍写「草稿更新未完成」，而 `README.md` 与 `draft_update.py`/Web API 已实现更新；历史多平台 Phase5 代码与 API 仍暴露，与「P0 仅微信」定位并存（见 §13）。 |
| **核心用户价值** | 在默认 mock 安全前提下，把本地写作流程变成可排期、可预检、可审计的微信草稿创建流水线，减少手工重复操作。 |
| **核心风险** | 误切 `WECHAT_MODE=real` 或误解「排期=微信后台定时」导致真实草稿残留或用户预期落差；本地 Web 无认证，绑定 `0.0.0.0` 会暴露管理接口。 |

---

## 4. 技术栈与运行方式

### 4.1 语言与框架

| 层 | 技术 |
|----|------|
| 语言 | Python ≥3.10（本机验证 3.14.5） |
| Web | FastAPI + Uvicorn |
| 前端 | 服务端渲染 HTML 模板 + 原生 JS/CSS（`admin_template.html` 等），无 React/Vue |
| CLI | `argparse` 多子命令（`cli.py`） |
| 包管理 | pip + `pyproject.toml`；Node 仅 MCP 辅助脚本 |

### 4.2 数据层

- **SQLite**（默认 `data/app.sqlite3`），SQLAlchemy 未使用，直连 `sqlite3`
- 核心表：`articles`、`publish_jobs`、`wechat_drafts`、`events`
- 扩展表：`collections`、`tags`、`remote_content_mirror`、`publish_proofs`、`operation_runs`、`scheduler_locks`、`weekly_plan_cursor` 等
- 迁移：`migrations/001..014` + `db.py` 基线 schema

### 4.3 外部服务（代码迹象，本轮未调用真实写操作）

| 服务 | 用途 | 默认行为 |
|------|------|----------|
| 微信公众号 API | token、素材、draft/add|update|delete、sync-remote | `WECHAT_MODE=mock` 不联网 |
| CDN jsdelivr | flatpickr 日期选择器样式 | Web UI 依赖外网 CSS |
| Google Stitch MCP | UI 设计输入 | 可选，需 `STITCH_API_KEY` |
| Playwright / Chrome DevTools MCP | 本地 UI 与微信后台辅助 | 开发验证，非运行时依赖 |
| GitHub MCP | 仓库操作 | 可选 token |
| AI/LLM | **未内置**；`INTERNAL_LLM_AGENT_ENABLED=false` | 外部 Agent 由用户自备 |

**未发现**：Redis、PostgreSQL、Prisma、支付、邮件、对象存储运行时依赖。

### 4.4 部署方式

- **无** Dockerfile / Compose / Vercel 配置
- `deploy/examples/scheduler/`：systemd unit、cron、`launchd` plist **示例**
- 推荐本机：`python -m wechat_article_scheduler.cli serve` + 可选 cron `run-once`
- **无** GitHub Actions CI 配置

### 4.5 测试体系

| 类型 | 现状 |
|------|------|
| 单元/集成 | pytest，`tests/` 108 文件，本轮 **457 passed, 1 skipped** |
| E2E | `tests/test_ui_e2e.py`、`test_web_*.py`（TestClient + 部分 Playwright） |
| Agent 门控 | `python scripts/agent_gate.py gate` → **PASS**（round_135） |
| Playwright MCP | 配置存在，本轮 UI 巡检使用 **cursor-ide-browser** |
| Lint/Typecheck | **无** 统一 `npm run lint` / mypy / ruff 入口 |

---

## 5. 当前成熟度判断

**等级：E（已接近可用产品）**

依据：

1. CLI 闭环 `init-db → scan → plan → run-once → scheduler` 已实现并有测试覆盖。
2. Web 工作台覆盖上传、排期、队列、草稿、回收站、预检、事件、帮助（浏览器快照验证页面可打开、结构完整）。
3. mock 模式默认可安全演练；real adapter 与 `scripts/real_api_check.py` 存在。
4. 外部 Agent 任务包、browser_assist 会话门控、远端镜像同步（round_135）已入代码与测试。
5. 未达 F：无正式容器/CI、无 Web 认证、scheduler 常驻运维仍依赖手工、部分 README「尚未完成」项仍 open。

---

## 6. 已识别功能清单

### 6.1 普通用户功能

| 功能 | 实现状态 | 入口 |
|------|----------|------|
| 浏览工作台首页 | ✅ | `http://127.0.0.1:8080/` |
| 上传作品/封面（md/txt/html + 图片） | ✅ | 首页拖拽/选择 + `POST /api/upload` |
| 扫描本地收件箱 | ✅ | 按钮 + `POST /api/scan` / CLI `scan` |
| 作品库列表、筛选合集 | ✅ | `#works` + `GET /api/articles` |
| 作品详情、预览、预检条 | ✅ | `/articles/{id}` |
| 单篇/批量排期 | ✅ | 弹窗 + `POST /api/articles/.../schedule` |
| 生成自动排期 | ✅ | `POST /api/plan` |
| 执行到点草稿创建 | ✅ | `POST /api/run-once`（mock 模拟） |
| 草稿队列查看、筛选、重试、取消 | ✅ | `#queue` + jobs API |
| 微信草稿记录页 | ✅ | `/drafts` + `GET /api/drafts` |
| 远端草稿镜像同步（real） | ✅ 代码存在 | `POST /api/sync-remote`；本库 DB 有 11 条 mock 镜像 |
| 远端草稿删除预览/执行 | ✅ 代码存在 | `POST /api/remote-delete/*`（需 real + 权限） |
| 回收站软删除/恢复/清空 | ✅ | trash API |
| 封面设置、批量封面、裁剪预览 | ✅ 部分 | cover API；双比例预览 README 称仍待完善 |
| 发布前检查/状态条 | ✅ | `GET /api/publish-preflight`、`preflight_bar` |
| 操作记录/事件时间线 | ✅ | `GET /api/events` |
| 帮助与三步引导 | ✅ | `#help` 区块 |
| 高级信息开关 | ✅ | localStorage 持久化 |
| 填写发布证明（人工确认） | ✅ | 详情页 + proof API |
| 导出 manual_export 包 | ✅ | 详情/列表「导出」 |
| 登录/注册 | **不适用** | 本地单用户工具，无认证 |

### 6.2 管理员 / 维护者功能

| 功能 | 状态 |
|------|------|
| 专用管理员后台 | **未发现**独立后台；与普通工作台合一 |
| Debug 面板 | ✅ `GET /debug`（HTTP 200） |
| 配置管理 UI | **部分**：通过 `.env` + `config/rules.yaml`，Web 无完整配置表单 |
| 调度健康检查 | ✅ CLI `scheduler-health` |
| 封面孤儿清理 | ✅ `/api/covers/*` |
| Agent 轮次状态 | ✅ `/api/agent-gate-status` |
| 运维 runbook dry-run | ✅ CLI `ops-health-dry-run` |

### 6.3 开发者 / 操作者功能

**CLI 子命令（节选，完整列表见 `cli.py --help`）**：

| 命令 | 用途 |
|------|------|
| `init-db` | 初始化 SQLite |
| `scan` / `plan` / `run-once` | 核心流水线 |
| `scheduler` / `scheduler-daemon` | 阻塞轮询调度 |
| `sync-remote` | 远端草稿/内容镜像同步 |
| `update-draft` | 更新已有微信草稿 |
| `export-agent-task(s)` | 导出外部 Browser Agent 任务包 |
| `browser-assist-session` | 浏览器辅助会话门控 |
| `real_api_check.py` | 真实 API 样本验证（需显式 real） |
| `agent_gate.py status/gate/advance` | 轮次门控 |
| `serve` | 启动 Web |
| `*-dry-run` 系列 | manifest/多项目/日历/unified-outbox 预研 |

**npm 脚本**：`check:mcp`、`check:stitch`、`check:cursor-mcp`（MCP 配置检查，非应用运行时）。

### 6.4 API 功能

Web 暴露 **70+** REST 端点（`app.py`）。按模块归类：

| 模块 | 代表路径 | 方法 | 认证 | 本地 mock 可测 |
|------|----------|------|------|----------------|
| 状态/概览 | `/api/status`, `/api/overview` | GET | 无 | ✅ |
| 文章 CRUD | `/api/articles`, `/api/articles/{id}` | GET/POST | 无 | ✅ |
| 上传/扫描/排期 | `/api/upload`, `/api/scan`, `/api/plan`, `.../schedule` | POST | 无 | ✅ |
| 队列/任务 | `/api/jobs`, `/api/jobs/{id}/retry` | GET/POST | 无 | ✅ |
| 草稿 | `/api/drafts`, `/api/remote-drafts` | GET | 无 | ✅ |
| 远端同步/删除 | `/api/sync-remote`, `/api/remote-delete/*` | POST | 无 | mock 可演练；real 需凭证 |
| 预检/字段矩阵 | `/api/publish-preflight`, `/api/wechat-field-matrix` | GET | 无 | ✅ |
| Browser assist | `/api/browser-assist/sessions/*` | GET/POST | 无 | ✅ 会话状态机 |
| 预研 dry-run | `/api/manifest/*`, `/api/video-package-plan` 等 | GET | 无 | ✅ 只读 JSON |
| 媒体 | `/media/cover/{article_id}` | GET | 无 | ✅ |

**安全说明**：所有 API 默认无认证，仅适合 `127.0.0.1` 本地使用。

### 6.5 数据处理功能

```text
1. 导入：inbox/imported 扫描 → parser 提取 title/summary/body → articles 表
2. 排期：rules.yaml + schedule_assign → publish_jobs（scheduled_at、config_json）
3. 执行：scheduler 认领 → adapter(mock/real) → wechat_drafts + events
4. 渲染：markdown → HTML（wechat renderer）
5. 封面：cover_assets 扫描/绑定/裁剪配置
6. 镜像：sync-remote → remote_content_mirror
7. 导出：manual_export outbox、external_agent task package
8. 审计：events、operation_runs、publish_proofs
```

### 6.6 AI / Agent 功能

| 项 | 说明 |
|----|------|
| 内置 LLM | **无**（`INTERNAL_LLM_AGENT_ENABLED=false`） |
| 外部 Browser Agent | 任务包导出至 `outbox/wechat_agent_tasks/`，含 `browser_agent_prompt.md`、`checklist.md` |
| Prompt 位置 | `external_agent/prompt_templates.py`、任务包内 markdown |
| 工具调用 | 项目不执行浏览器；用户将 prompt 交给 Cursor/Hermes/Playwright MCP |
| 审核机制 | `publish_proofs` + `waiting-confirmation` 状态；非内容审核，是发布/后台操作人工确认 |
| 失败处理 | 任务 `failed` + `retry-failed`；事件日志记录 |
| 人工确认节点 | browser_assist 会话：`confirm-login` → `confirm-schedule-setup` → proof |

---

## 7. 本地启动与验证结果

### 7.1 依赖安装

| 命令 | 结果 |
|------|------|
| `.venv` 存在 | ✅ 本机已有虚拟环境 |
| `pip install -r requirements.txt` | 未重跑（venv 已满足） |
| `.venv/bin/pip check` | **No broken requirements found** |
| `npm install` | 未执行（仅 MCP 检查，非必需） |
| 系统 `python3 -m pytest` | **失败**：`No module named pytest`（未用 venv） |

### 7.2 环境变量检查

- `.env.example` 存在，涵盖 `WECHAT_MODE`、DB 路径、Web 端口、Agent outbox 等
- 本机 `.env`、`config/rules.yaml` 存在（**未读取敏感值**）
- 本轮启动使用显式 `WECHAT_MODE=mock` 覆盖，避免误联网

### 7.3 数据库初始化

| 命令 | 结果 |
|------|------|
| `.venv/bin/python -m wechat_article_scheduler.cli init-db` | ✅ `数据库已初始化: .../data/app.sqlite3` |
| 现有数据统计 | articles:22, publish_jobs:43, wechat_drafts:22, events:418, remote_content_mirror:11 |

### 7.4 Lint 结果

**命令不存在**。仓库无 ruff/mypy/eslint 统一入口；质量依赖 pytest + agent_gate。

### 7.5 Typecheck 结果

**命令不存在**（无 mypy/pyright 配置）。

### 7.6 Build 结果

**不适用**。纯 Python 包，无前端 build 链；`pip install -e .` 为可选开发安装。

### 7.7 Test 结果

```text
.venv/bin/python -m pytest --tb=no -q
→ 457 passed, 1 skipped, 1 warning in 44.94s

python scripts/agent_gate.py gate
→ Agent gate: PASS (round=round_135)
```

### 7.8 Dev Server 结果

| 尝试 | 结果 |
|------|------|
| `python3 -m wechat_article_scheduler.cli serve`（无 venv） | ❌ `ModuleNotFoundError: wechat_article_scheduler` |
| `.venv/bin/python -m wechat_article_scheduler.cli serve --host 127.0.0.1 --port 8080` + `WECHAT_MODE=mock` | ✅ `Uvicorn running on http://127.0.0.1:8080` |
| `curl http://127.0.0.1:8080/` | ✅ 200 |
| `curl http://127.0.0.1:8080/api/status` | ✅ JSON，`wechat_mode: mock` |
| `curl http://127.0.0.1:8080/debug` | ✅ 200 |

---

## 8. 界面 / 页面 / 交互巡检结果

**工具**：`cursor-ide-browser`（本地 Web）；**未**使用 `wechat-chrome-session`（公众号后台不在本轮范围）。

### 8.1 已巡检页面

| 页面 | URL | 可打开 | 明显报错 | 空白/404 | 文案可读 | 主要操作可见 |
|------|-----|--------|----------|----------|----------|--------------|
| 工作台首页 | `/` → `#works` | ✅ | 无 | 无 | ✅ 标题+副标题+帮助 | ✅ 上传/扫描/排期/队列 |
| 微信草稿页 | `/drafts` | ✅ | 无 | 无 | ✅ | ✅ 筛选按钮 |
| 作品详情 | `/articles/63` | ✅ | 无 | 无 | ✅ 分区标题清晰 | ✅ 预检/预览/proof 区 |
| Debug | `/debug` | ✅（curl） | - | 无 | 开发者向 | - |

### 8.2 Console / Network

- 通过 `browser_cdp` → `Runtime.evaluate` 检查：`window.__consoleErrors` 为空（页面未注入捕获器，**不能等同于完整 console 审计**）。
- 核心 API（`/api/status`、`/api/articles`、`/api/queue-summary`）curl 均 200。
- **未完成**：Playwright MCP `browser_console_messages`（cursor-ide-browser 无此工具）；Network 面板逐请求审计。

### 8.3 交互观察

- 首页初始有「读取中…」禁用按钮，随后数据加载完成（API 有 22 篇文章、队列 summary 正常）。
- 批量操作按钮在无选中时 disabled，符合预期。
- 「帮助」区明确说明三步流程与 draft-only 语义。
- 「显示高级信息」开关存在；默认普通视图信息密度较高但可理解。
- 远端草稿区有 11 条 mock 镜像数据（演练模式）。

### 8.4 移动端 / 小屏幕

**本轮未完成 viewport 缩放截图**：`browser_resize` 工具不可用。代码有 `viewport` meta 与响应式 CSS，历史报告 `docs/reports/ui_review/` 有 375/768/1280 截图可参考。

### 8.5 空状态

- `articles/inbox` 当前为空；`scan` 返回 `scanned: 0`。
- 作品库仍有 22 篇 imported 数据，**非空状态**；空状态 UX 需用隔离 DB 另测。

---

## 9. 用户角色与用户路径

### 角色

| 角色 | 描述 |
|------|------|
| **内容运营者（主）** | 上传/排期/查看队列与草稿，偶尔填 proof |
| **维护者** | 配置 `.env`、跑 scheduler、real API 验证、清理测试草稿 |
| **外部 Browser Agent 操作者** | 消费 `outbox/wechat_agent_tasks` 任务包，在公众号后台核对 |
| **仓库开发者/Agent** | pytest、agent_gate、轮次推进 |

---

### 路径 1：首次访问

```text
路径编号：P-01
路径名称：首次打开工作台理解项目
用户角色：新用户
入口：http://127.0.0.1:8080/
操作步骤：阅读页眉「本地·安全发布」→ 安全状态区 → 帮助区三步说明
成功标准：用户理解「演练/真实模式」「排期≠微信后台定时」「下一步点上传或扫描」
当前是否可完成：是（mock 模式标题与帮助文案清晰）
阻塞点：无
风险：信息量大，普通用户可能忽略「后台发布需人工」
后续是否值得重点测试：是
```

### 路径 2：上传并排期（核心）

```text
路径编号：P-02
路径名称：上传作品 → 批量排期 → 队列可见
用户角色：内容运营者
入口：首页上传区 / 扫描收件箱
操作步骤：选择 md+封面 → 上传 → 选中作品 → 批量草稿排期 → 设时间/间隔 → 确认
成功标准：作品库出现记录；队列有 pending；预检条显示 ready/warn
当前是否可完成：是（测试库有数据；inbox 空时需先上传）
阻塞点：inbox 空时须走上传而非扫描
风险：空文件/无标题内容可能被接受（见问题 P1-002）
后续是否值得重点测试：是（最高优先级）
```

### 路径 3：到点创建草稿（mock）

```text
路径编号：P-03
路径名称：执行到点草稿创建（演练）
用户角色：内容运营者
入口：主操作「执行到点草稿创建」
操作步骤：确保有 due 任务 → 点击执行 → 查看队列 completed + 微信草稿区
成功标准：mock media_id 写入；事件记录；队列计数变化
当前是否可完成：是（API 显示 due_now: 1, pending: 12, done: 31）
阻塞点：无（mock）
风险：用户可能误以为已在微信后台定时
后续是否值得重点测试：是
```

### 路径 4：作品详情预览与 proof

```text
路径编号：P-04
路径名称：详情页预检 → 预览 → 填写证明
用户角色：运营者 / 人工确认者
入口：作品卡片「详情」
操作步骤：查看预检条 → 公众号正文预览 → 填写 proof 表单
成功标准：预检项可读；预览渲染；proof POST 成功
当前是否可完成：是（页面结构完整）
阻塞点：browser_assist 需真实 Chrome 会话（本轮未测）
风险：proof 与微信后台真实状态可能不一致
后续是否值得重点测试：是
```

### 路径 5：回收站与恢复

```text
路径编号：P-05
路径名称：删除作品 → 回收站恢复
用户角色：内容运营者
入口：作品库删除 / #trash
操作步骤：删除选中 → 回收站恢复 → 确认排期不自动恢复提示
成功标准：软删除与恢复 API 200；文案提示排期需重设
当前是否可完成：是（pytest `test_web_trash` 覆盖）
阻塞点：无
风险：用户可能以为恢复即恢复排期
后续是否值得重点测试：中
```

### 路径 6：远端同步与删除（real）

```text
路径编号：P-06
路径名称：同步远端草稿 → 预览删除 → 执行删除
用户角色：维护者
入口：微信草稿区「同步远端草稿」
操作步骤：sync-remote → 勾选 → 删除影响预览 → 执行删除
成功标准：mirror 表更新；real 下 draft/delete 成功
当前是否可完成：mock 下仅镜像演练；real 需凭证与权限
阻塞点：本轮未执行真实删除
风险：误删真实草稿；freepublish 列表可能无权限
后续是否值得重点测试：是（需隔离 real 环境）
```

### 路径 7：新手上手（README）

```text
路径编号：P-07
路径名称：按 README 从零启动
用户角色：新开发者
入口：README 快速开始
操作步骤：venv → pip install → cp .env → init-db → serve
成功标准：8080 可访问
当前是否可完成：是（用 .venv/bin/python）；若只用 python3 无安装会失败
阻塞点：必须先 pip install -e . 或 PYTHONPATH
风险：文档写 python3 -m，未强调 venv 激活
后续是否值得重点测试：是
```

### 路径 8：错误恢复

```text
路径编号：P-08
路径名称：失败任务重试与预检阻塞提示
用户角色：运营者
入口：队列「失败」筛选
操作步骤：查看 failure_digest → 重试 → 查看事件日志
成功标准：失败原因人话化；重试后状态变化
当前是否可完成：是（当前 failed_count: 0，需构造失败场景）
阻塞点：无失败样本时无法目视验证
风险：-
后续是否值得重点测试：中
```

---

## 10. 初步测试用例素材

### A. 首次访问 / 首次使用

```text
用例编号：TC-A01
用例名称：首页三步帮助可读性
项目模块：Web 工作台 / 帮助
用户角色：新用户
前置条件：mock 模式 serve 已启动
测试步骤：打开 / → 滚动至帮助 → 阅读模式说明与三步流程
预期结果：明确「演练不联网」「排期是本地到点创建草稿」「后台发布人工」
当前是否可测：是
当前阻塞点：无
优先级：P1
备注：配合顶部 publish_policy headline 交叉验证
```

### B. 核心功能闭环

```text
用例编号：TC-B01
用例名称：上传→排期→run-once→草稿记录
项目模块：核心流水线
用户角色：运营者
前置条件：空 inbox 或新隔离 DB
测试步骤：上传 sample.md → 批量排期 1 小时后 → run-once（或等待 auto_run_due）
预期结果：publish_jobs 完成；wechat_drafts 有记录；事件有 create 类条目
当前是否可测：是
当前阻塞点：无
优先级：P0
备注：应用隔离 DATABASE_PATH 避免污染主库
```

### C. 数据输入

```text
用例编号：TC-C01
用例名称：空 Markdown 文件导入拒绝
项目模块：上传/扫描
用户角色：运营者
前置条件：serve + 空 .md 文件
测试步骤：仅上传空 md → 查看是否进入作品库
预期结果：应拒绝或标为错误，不入库
当前是否可测：是
当前阻塞点：历史报告记为失败（P1-002）
优先级：P1
备注：回归 2026-06-06 用户测试结论
```

```text
用例编号：TC-C02
用例名称：批量间隔排期 3 小时
项目模块：排期
用户角色：运营者
前置条件：≥3 篇作品
测试步骤：批量排期，间隔 3 小时 → 刷新 → 核对 scheduled_at
预期结果：时间递增 3h
当前是否可测：是
当前阻塞点：无
优先级：P1
```

### D. 数据输出

```text
用例编号：TC-D01
用例名称：导出外部 Agent 任务包
项目模块：external_agent
用户角色：维护者
前置条件：已有 draft_created 任务
测试步骤：CLI export-agent-task --job-id N → 检查 outbox 目录文件齐全
预期结果：task.json、browser_agent_prompt.md、checklist.md 存在且无密钥
当前是否可测：是
当前阻塞点：无
优先级：P1
```

### E. 权限与身份

```text
用例编号：TC-E01
用例名称：Web 未授权访问
项目模块：安全
用户角色：不适用
前置条件：-
测试步骤：-
预期结果：-
当前是否可测：不适用
当前阻塞点：项目无登录体系；需测的是「勿绑定 0.0.0.0」
优先级：P2
备注：改为测 WEB_HOST 默认 127.0.0.1
```

### F. 错误状态

```text
用例编号：TC-F01
用例名称：无 WECHAT 凭证时 real 模式预检提示
项目模块：预检/配置
用户角色：维护者
前置条件：WECHAT_MODE=real 且 AppID 空
测试步骤：打开首页预检 / real_api_check --dry-run
预期结果：阻塞原因清晰，不崩溃
当前是否可测：是
当前阻塞点：勿打印真实密钥
优先级：P1
```

### G. 空状态

```text
用例编号：TC-G01
用例名称：全新 DB 首页空作品库
项目模块：Web 空状态
用户角色：新用户
前置条件：新 init-db + 无 articles
测试步骤：打开 / → 查看作品库与主操作提示
预期结果：空状态文案指向「上传或扫描」
当前是否可测：是
当前阻塞点：需临时 DB
优先级：P2
```

### H. 移动端 / 小屏幕

```text
用例编号：TC-H01
用例名称：375px 宽度无横向溢出
项目模块：响应式
用户角色：运营者
前置条件：Playwright 或 chrome-devtools 设 viewport 375
测试步骤：打开首页/详情 → 截图对比
预期结果：关键按钮可点、无严重溢出
当前是否可测：是（需浏览器 resize）
当前阻塞点：本轮未执行
优先级：P2
```

### I. 性能与加载

```text
用例编号：TC-I01
用例名称：22 篇文章列表首屏加载
项目模块：Web 性能
用户角色：运营者
前置条件：当前种子 DB
测试步骤：硬刷新 / → 记录 API 往返与可交互时间
预期结果：<3s 可交互（本地预期）
当前是否可测：是
当前阻塞点：无
优先级：P3
```

### J. 可访问性与可读性

```text
用例编号：TC-J01
用例名称：主操作按钮文案与 disabled 状态
项目模块：a11y/UX
用户角色：运营者
前置条件：无选中作品
测试步骤：检查「批量设置封面」等是否 disabled 且有上下文
预期结果：disabled 合理；帮助区解释原因
当前是否可测：是
当前阻塞点：无
优先级：P2
```

### K. 管理后台 / 维护功能

```text
用例编号：TC-K01
用例名称：scheduler-health CLI
项目模块：运维
用户角色：维护者
前置条件：有 publish_jobs 数据
测试步骤：cli scheduler-health
预期结果：输出队列/锁/卡住任务摘要，exit 0
当前是否可测：是
当前阻塞点：无
优先级：P2
```

### L. 部署与交付

```text
用例编号：TC-L01
用例名称：deploy 示例 plist 与文档一致性
项目模块：部署
用户角色：维护者
前置条件：阅读 deploy/examples/scheduler/README.md
测试步骤：核对 cron run-once 与 scheduler-daemon 说明
预期结果：路径与 venv python 可手工落地
当前是否可测：是（文档走查）
当前阻塞点：无自动化 CI 验证
优先级：P3
```

---

## 11. 已发现问题清单

### P0 阻塞（0 项）

本轮未发现「无法启动或核心入口完全不可用」的 P0。注意：裸 `python3` 无安装会启动失败，属环境配置问题，README 已写 venv 流程。

---

### P1 严重（4 项）

```text
问题编号：P1-001
问题等级：P1
问题位置：配置语义 /api/status
复现方式：WECHAT_ENABLE_PUBLISH=false 时查看 status.publish_policy 与 web_auto_publish
实际表现：publish_enabled: false，但 web_auto_publish: true 仍出现
期望表现：普通用户视图应统一「只创建草稿、不自动正式发布」叙事
可能原因：web_auto_publish 字段历史命名，与 draft-only 语义混淆
建议修复方向：普通视图合并文案；或重命名字段并更新测试
是否需要后续测试 Prompt 覆盖：是
```

```text
问题编号：P1-002
问题等级：P1
问题位置：上传/扫描解析
复现方式：上传空 .md（见 docs/reports/user_view_function_test_2026-06-06.md）
实际表现：空文件可能作为正常作品入库
期望表现：拒绝或明确错误态
可能原因：parser/扫描缺少最小内容校验
建议修复方向：增加空文件/无标题门禁 + 测试
是否需要后续测试 Prompt 覆盖：是
```

```text
问题编号：P1-003
问题等级：P1
问题位置：排期算法 / weekly_plan_cursor
复现方式：draft-only 账号连续两周 plan（用户测试报告 §3-17）
实际表现：第二周可能重复第一周同一批作品时间槽
期望表现：续排应推进游标或排除已完成稿
可能原因：每周游标/去重逻辑不完善
建议修复方向：核对 round_135 后 weekly 续排测试
是否需要后续测试 Prompt 覆盖：是
```

```text
问题编号：P1-004
问题等级：P1
问题位置：真实 API 路径
复现方式：sync-remote / remote-delete / real draft 在无凭证环境
实际表现：无法在本轮完成真实端到端
期望表现：预检清晰阻塞；有凭证时可完成
可能原因：设计如此；需隔离测试环境
建议修复方向：后续测试用专用 AppID + 测试草稿清理 SOP
是否需要后续测试 Prompt 覆盖：是（标注「需 real 凭证」）
```

---

### P2 中等（5 项）

```text
问题编号：P2-001
问题等级：P2
问题位置：文档 / 环境
复现方式：直接 python3 -m wechat_article_scheduler.cli serve（无 venv）
实际表现：ModuleNotFoundError
期望表现：README 强调必须 venv 或 pip install -e .
可能原因：包未安装到系统 Python
建议修复方向：README 增加故障排查一行
是否需要后续测试 Prompt 覆盖：是（新手上手路径）
```

```text
问题编号：P2-002
问题等级：P2
问题位置：docs/current_state_audit.md
复现方式：对比 README 与 draft_update API
实际表现：审计文档仍列「草稿更新未完成」
期望表现：与代码一致
可能原因：文档未随 round 刷新
建议修复方向：同步审计文档
是否需要后续测试 Prompt 覆盖：否（文档债）
```

```text
问题编号：P2-003
问题等级：P2
问题位置：Web UI 依赖
复现方式：断网打开工作台
实际表现：flatpickr CSS 从 cdn.jsdelivr.net 加载
期望表现：离线可用或内置静态资源
可能原因：CDN 引用
建议修复方向：vendor 本地化（可选）
是否需要后续测试 Prompt 覆盖：可选
```

```text
问题编号：P2-004
问题等级：P2
问题位置：Web 安全模型
复现方式：API 无 token 访问 /api/run-once
实际表现：任何能访问端口的客户端可触发执行
期望表现：本地单用户可接受；公网暴露需防护
可能原因：信任本地绑定
建议修复方向：文档警告勿 WEB_HOST=0.0.0.0；可选简单 token
是否需要后续测试 Prompt 覆盖：是（安全场景）
```

```text
问题编号：P2-005
问题等级：P2
问题位置：质量门禁
复现方式：查找 lint/typecheck 命令
实际表现：不存在统一入口
期望表现：可选 ruff/mypy 集成
可能原因：项目以 pytest 为主
建议修复方向：后续加轻量 lint
是否需要后续测试 Prompt 覆盖：否
```

---

### P3 轻微（3 项）

```text
问题编号：P3-001
问题等级：P3
问题位置：首页加载态
复现方式：打开 / 首屏
实际表现：短暂「读取中…」禁用按钮
期望表现：骨架屏或更快首屏
可能原因：并行拉取 overview/articles/jobs
建议修复方向：UX 抛光
是否需要后续测试 Prompt 覆盖：可选
```

```text
问题编号：P3-002
问题等级：P3
问题位置：移动端
复现方式：375px 未本轮截图
实际表现：未知（历史 ui_review 有基线）
期望表现：基本可读可点
可能原因：-
建议修复方向：Playwright 三 viewport 回归
是否需要后续测试 Prompt 覆盖：是
```

```text
问题编号：P3-003
问题等级：P3
问题位置：pytest warning
复现方式：pytest 全量
实际表现：StarletteDeprecationWarning httpx vs httpx2
期望表现：无警告或迁移 httpx2
可能原因：FastAPI TestClient 依赖
建议修复方向：依赖升级
是否需要后续测试 Prompt 覆盖：否
```

---

### P4 建议（4 项）

```text
问题编号：P4-001 — 多平台预研 API 仍挂在 Web（dry-run），易让新用户以为已支持知乎/抖音等 → 普通视图隐藏或标「预研」
问题编号：P4-002 — Markdown→微信 HTML 排版与公众号预览准确度（README 尚未完成项）
问题编号：P4-003 — 封面双比例裁剪预览完善
问题编号：P4-004 — 增加 GitHub Actions 跑 pytest 作为交付信号
```

---

## 12. 不可测、缺失或仅规划的功能

| 项 | 分类 | 说明 |
|----|------|------|
| 微信后台定时发布写入 | 平台限制 | API 不支持；靠 browser_assist + 人工 |
| 多平台真实发布（知乎/豆瓣/B站等） | 文档规划/backlog | 仅有 dry-run / manual_export 骨架 |
| 内置 Browser Agent | 明确不做 | 外置任务包模式 |
| 内置 LLM 内容生成 | 未实现 | - |
| 团队协作/多用户 | 未实现 | 单用户本地 |
| Web 登录认证 | 未实现 | - |
| Docker 一键部署 | 未实现 | 仅示例脚本 |
| CI/CD | 未实现 | 无 `.github/workflows` |
| 真实 freepublish 列表同步 | 权限/账号相关 | 部分账号 API 未授权 |
| 本轮真实微信删除/发布 | 测试限制 | 禁止执行真实写操作 |

---

## 13. 文档与代码不一致之处

1. **`docs/current_state_audit.md`**：列「草稿更新未完成」，但 `update-draft` CLI、`POST /api/articles/{id}/update-draft` 与测试已存在。
2. **`docs/current_state_audit.md`**：迁移范围写 `001..008`，实际已有 `014`。
3. **用户测试报告（2026-06-06）**：称「无远端同步」——**已过时**；`sync-remote`、`remote_content_mirror` 表与 Web UI 已在 round_135 实现。
4. **README「尚未完成」** vs **代码**：封面裁剪预览、scheduler 常驻手册部分已有实现痕迹，但体验仍未达 README 期望。
5. **Phase5 预研模块**：`project.yaml` 称 P0 仅微信，但 Web 仍暴露 `video-package-plan`、`short-video-plan` 等 API（干跑）。

---

## 14. 部署与交付可用性判断

| 维度 | 判断 |
|------|------|
| 本地开发 | ✅ 成熟：venv + init-db + serve |
| 生产打包 | ⚠️ 无容器/无锁版本发布流程；靠 cron/systemd 示例 |
| 配置交付 | ✅ `.env.example` + `rules.example.yaml` 齐全 |
| 数据迁移 | ✅ migrations + init-db 自动应用 |
| 监控 | ⚠️ 事件表 + 日志文件；无 Prometheus 等 |
| 回滚 | ⚠️ SQLite 文件级备份为主 |
| 安全交付 | ⚠️ 依赖用户不提交 `.env`、不暴露 Web 到公网 |

**结论**：适合**个人本机/家庭服务器**交付；**不具备**开箱即用的云原生运营能力（F 级）。

---

## 15. 适合下一阶段重点测试的路径

1. **P-02 上传→批量排期→队列持久化**（核心闭环，隔离 DB）
2. **P-03 到点 run-once / auto_run_due**（mock 与 real 双轨，强调 draft-only 文案）
3. **P-06 远端同步与删除**（real 凭证 + 测试草稿清理 SOP，禁止正式发布）

次要：**P-07 新手上手**、**P-04 proof 回填**、**TC-C01 空文件拒绝回归**。

---

## 16. 对后续个性化测试 Prompt 的建议

1. **强制隔离环境**：`DATABASE_PATH=/tmp/wcas-test.sqlite3`、`WECHAT_MODE=mock`、`ARTICLES_INBOX=/tmp/...`；真实 API 子集另开 prompt。
2. **角色分轨**：「普通运营者」只看关闭高级信息的首页；「维护者」才看 debug/real API/远端删除。
3. **语义重点**：反复验证「本地排期 ≠ 微信后台定时」「演练模式不联网」是否在每个关键按钮旁得到确认。
4. **证据要求**：每条路径需 HTTP 状态码 + 至少一张截图 + 队列/事件 DB 查询或 API 摘要。
5. **禁止项写入 Prompt**：不得 `WECHAT_ENABLE_PUBLISH=true` 点正式发布；不得未确认删除真实草稿。
6. **回归清单**：纳入 `test_user_view_rounds_abcd`、`test_external_agent_task_package`、`test_wechat_chain_stability` 对应用户场景。
7. **浏览器工具**：本地 Web 用 playwright/chrome-devtools；`mp.weixin.qq.com` **仅** wechat-chrome-session。
8. **区分 bug vs 规划**：多平台 API 返回 dry-run JSON 视为「预研占位」，非 P0 缺陷。

---

## 17. 附录：执行过的命令与结果摘要

| # | 命令 | 结果摘要 |
|---|------|----------|
| 1 | `ls -la .env config/rules.yaml data/app.sqlite3; python3 --version` | 文件存在；Python 3.14.5 |
| 2 | `npm run check:mcp` | PASS，7 个 MCP server |
| 3 | `python3 -m pytest`（无 venv） | 失败：No module named pytest |
| 4 | `.venv/bin/python -m pytest --tb=no -q` | **457 passed, 1 skipped**, 44.94s |
| 5 | `python scripts/agent_gate.py status` | round_135 completed |
| 6 | `python scripts/agent_gate.py gate` | **PASS** |
| 7 | `python3 -m wechat_article_scheduler.cli serve`（无 venv） | ModuleNotFoundError |
| 8 | `WECHAT_MODE=mock .venv/bin/python -m ... cli serve --port 8080` | Uvicorn running :8080 |
| 9 | `curl http://127.0.0.1:8080/api/status` | 200, wechat_mode=mock |
| 10 | `curl http://127.0.0.1:8080/api/overview` | 200 |
| 11 | `curl http://127.0.0.1:8080/api/articles?limit=3` | 200, 有预检条数据 |
| 12 | `curl http://127.0.0.1:8080/api/queue-summary` | due_now:1, pending:12, done:31 |
| 13 | `curl http://127.0.0.1:8080/debug` | 200 |
| 14 | `.venv/bin/python -m ... cli init-db` | 数据库已初始化 |
| 15 | `.venv/bin/python -m ... cli scan` | scanned:0（inbox 空） |
| 16 | `.venv/bin/pip check` | No broken requirements |
| 17 | SQLite 表计数脚本 | articles:22, jobs:43, drafts:22, events:418, mirror:11 |
| 18 | cursor-ide-browser 打开 `/`, `/drafts`, `/articles/63` | 页面可渲染，结构完整 |
| 19 | browser_cdp Runtime.evaluate | 无注入 console 错误 |

**未执行**：`WECHAT_MODE=real` 联网写操作、`wechat-chrome-session` 公众号后台、`npm run lint`（不存在）、Docker build、移动端 resize 截图。

---

*报告结束。如有轮次或功能变更，请在本文件顶部更新生成时间与 round 引用。*
