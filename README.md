# wechat-article-scheduler

本项目定位为**本地微信公众号文章发布工作台**：以 CLI 为主，Web 控制台作为电脑浏览器优先的本地工作台，围绕本地内容扫描、排期、草稿创建与可审计发布流程构建闭环，默认安全保守。

## 核心特性

- 保留现有 CLI 闭环：`scan` / `plan` / `run-once` / `scheduler`
- 默认 `WECHAT_MODE=mock`，不开启真实 API 调用
- 摘要（digest）统一上限 **120 字**，上传前会再次兜底截断
- 事件审计可追溯：扫描、排期、执行、失败、截断 warning 均写入 `events`
- Web 控制台原则：普通用户视图优先 + Desktop-first local workbench；手机/平板只做不横向溢出、关键按钮可点、页面可读的兼容

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/rules.example.yaml config/rules.yaml
python -m wechat_article_scheduler.cli init-db
```

将 `.md` / `.txt` / `.html` 放入 `articles/inbox/` 后执行：

```bash
python -m wechat_article_scheduler.cli scan
python -m wechat_article_scheduler.cli plan
python -m wechat_article_scheduler.cli run-once
```

仓库已纳入 `articles/imported/`、`articles/published/` 下的章节样稿，供 Agent 与本地测试 scan/plan 流程使用（不提交 `.env` 与运行时数据库）。

## 运行模式（三种）

1. `mock`（默认）：不联网，生成本地 mock 草稿/发布结果
2. `real + WECHAT_ENABLE_PUBLISH=false`：只创建真实草稿，不提交发布
3. `real + WECHAT_ENABLE_PUBLISH=true`：创建草稿并提交发布（需人工确认后使用）

## CLI 命令

| 命令 | 说明 |
|------|------|
| `init-db` | 初始化 SQLite |
| `scan` | 扫描 inbox、去重、入库 |
| `plan` | 生成 `publish_jobs` |
| `run-once` | 执行到期任务 |
| `scheduler` | 后台轮询调度 |
| `reject --article-id N` | 驳回文章 |
| `retry-failed` | 重置失败任务为待执行 |
| `events --limit N` | 查看审计事件 |
| `serve` | 启动本地 FastAPI 管理页 |

## 配置说明

- `.env`：环境变量（只放本地，不提交）
- `config/rules.yaml`：扫描、去重、排期与 `summary_max_chars`（默认 120）

## 文档索引与路线图

- 文档入口：`docs/index.md`
- 当前状态审计：`docs/current_state_audit.md`
- 产品愿景：`docs/product_vision.md`
- 架构说明：`docs/architecture.md`
- 轮次路线图：`docs/rounds.md`
- 迁移计划：`docs/migration_plan.md`
- 可用性诊断（面向非技术用户）：`docs/web_console_usability_review.md`

路线图现在按 Phase / Round 0-38 维护，每轮都要求目标、非目标、验收、建议测试与退出标准，并由 `scripts/agent_gate.py` 与 `tests/test_agent_gate.py` 做同步校验。Phase 6 / Phase 7 / Phase 8（Round 19–38）是普通用户友好的 Web 工作台可用性专项：普通视图只展示安全状态、下一步、操作结果和错误恢复建议；数据库路径、原始 JSON、内部字段等进入高级信息开关。电脑浏览器是默认形态，窄屏只作为兼容验收。

## 安全边界

- 默认不自动发布真实公众号内容（建议先使用 mock 或 real-draft-only）
- 不提交 `.env`、密钥、token、cookie
- 不使用网页模拟登录公众号后台
- 日志不打印 access token / secret
