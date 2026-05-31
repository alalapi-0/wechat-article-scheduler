# wechat-article-scheduler

本项目定位为**本地「作品 → 公众号」批量发布工作台**：用户在网页**批量上传文章与封面**，上传即视为想发布的作品，**没有"审核"步骤**。以 CLI 为基础闭环，Web 控制台作为电脑浏览器优先的本地工作台，围绕上传、排期、草稿创建与可审计发布构建闭环，默认安全保守。

## 核心特性

- 网页**批量上传作品与封面**：拖拽即可收录，封面按文件名自动绑定到同名作品，每篇可单独换封面
- CLI 闭环：`scan` / `plan` / `run-once` / `scheduler`（上传内部复用 scan 入库）
- 默认 `WECHAT_MODE=mock`，不开启真实 API 调用
- 摘要（digest）统一上限 **120 字**，发布前会再次兜底截断
- 无审核流程：安全靠默认演练 + 显式发布开关 + 发布前二次确认 + 预检清单
- 事件审计可追溯：上传/扫描、排期、执行、失败、截断 warning 均写入 `events`
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

启动 Web 工作台后，可直接在「作品库」**拖拽上传**文章与封面；或用 CLI：将 `.md` / `.txt` / `.html` 放入 `articles/inbox/` 后执行：

```bash
python -m wechat_article_scheduler.cli serve   # 浏览器打开 http://127.0.0.1:8080/ 上传与排期
# 或纯命令行：
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
| `reject --article-id N` | 从发布流程移除某篇作品 |
| `retry-failed` | 重置失败任务为待执行 |
| `events --limit N` | 查看审计事件 |
| `serve` | 启动本地 FastAPI 工作台（含网页批量上传） |

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

路线图现在按 Phase / Round 0-46 维护，每轮都要求目标、非目标、验收、建议测试与退出标准，并由 `scripts/agent_gate.py` 与 `tests/test_agent_gate.py` 做同步校验。Phase 6 / Phase 7 / Phase 8（Round 19–38）是普通用户友好的 Web 工作台可用性专项；**Phase 10（Round 43–46）完成产品重定位**：移除审核概念、新增网页批量上传作品与封面、重构工作台界面与配色。电脑浏览器是默认形态，窄屏只作为兼容验收。

## 安全边界

- 默认不自动发布真实公众号内容（建议先使用 mock 或 real-draft-only）
- 不提交 `.env`、密钥、token、cookie
- 不使用网页模拟登录公众号后台
- 日志不打印 access token / secret
