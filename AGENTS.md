# AGENTS.md

本文件是 wechat-article-scheduler 的唯一项目级 Agent 规则。README 面向使用者；docs 解释产品和运维；它们不能覆盖本文件的权限与安全边界。

## 产品边界

本项目是个人本地微信公众号草稿工作台，主流程只有：

1. 导入并去重本地文章；
2. 生成本地排期；
3. 到点创建或更新微信公众号草稿；
4. 导出外部 Agent 任务包；
5. 由用户在公众号后台完成最终发布，并回填真实 proof。

默认 WECHAT_MODE=mock，不联网。WECHAT_MODE=real 只允许调用 token、素材、草稿创建/更新以及只读同步接口。项目代码不得调用 freepublish/submit 或 draft/delete，不得自动发布、群发、删除远端草稿或确认后台定时发布。

知乎、豆瓣、小红书、视频号、Bilibili、抖音、快手、博客、Webhook、视频与音频内容包均不属于当前运行时；未来想法只记录在 docs/backlog.md，不提前实现。

## 工作方式

- 先用 rg、rg --files 和精确路径读取与任务有关的内容；不要固定全文读取历史报告或整个 docs。
- 现有代码、测试和文档是证据，不是必须保留的历史包袱。确认废弃的实现及其测试、配置和文档应在同一改动中移除。
- 只改当前任务拥有的路径。工作树可能包含用户改动；不得回退、覆盖或顺手提交无关内容。
- 使用 apply_patch 编辑文件。批量删除前先列出精确目标并确认其可由 Git 恢复；不得创建备份树、.bak 文件或永久临时文件。
- 未经用户明确要求，不 commit、push、merge、deploy 或 publish。

## 受保护内容

默认不得读取、打印、修改或删除：

- .env、token、AppSecret、cookie、浏览器 profile/session、key 和 pem；
- data/app.sqlite3、config/rules.yaml、data/logs/**、storage/**；
- articles/** 中的用户文章、封面和发布状态；
- 与任务无关的未提交改动。

.env.example 和 config/rules.example.yaml 可在配置接口变化时更新，但不得写入真实值。真实微信 API 只在用户明确要求、凭证由本地环境提供且目标仍是草稿或只读同步时使用。遇到扫码、验证码、风控或最终发布确认必须停止并交还用户。

## 技术事实

- Python >= 3.10，setuptools，src layout。
- SQLite 本地存储；默认 data/app.sqlite3。
- FastAPI + Uvicorn，前端为服务端 HTML/CSS/JavaScript。
- PyYAML、python-dotenv、httpx、python-multipart。
- pytest；Playwright 只用于本地 Web E2E/诊断。
- 没有 Node 运行时、前端构建链、Redis、PostgreSQL 或 Celery。

## 常用命令

Linux 默认入口使用固定存储守卫和专属解释器；不读取旧配置或用户数据：

    python3 -I -B scripts/storage_runtime.py check
    python3 -I -B scripts/storage_runtime.py cli init-db
    python3 -I -B scripts/storage_runtime.py cli serve

核心 CLI：

    python3 -I -B scripts/storage_runtime.py cli scan
    python3 -I -B scripts/storage_runtime.py cli plan
    python3 -I -B scripts/storage_runtime.py cli run-once
    python3 -I -B scripts/storage_runtime.py cli scheduler-health

实际命令清单以此为准：

    python3 -I -B scripts/storage_runtime.py cli --help

## 验证

- 所有改动：检查 git status --short、git diff、git diff --check。
- Python 代码：先跑 `python3 -I -B scripts/storage_runtime.py test`，再用 `python3 -I -B scripts/test_linux_profile.py current` 跑完整测试。后者复制受控源码、测试与合成 fixtures 到私有临时目录，测试和普通 Python 子进程的默认加载器只见空临时配置；原 `.env`、rules、数据库、articles 和 storage 不进入副本。失败/跳过保留，不可据此声称真实微信验收。
- 文档/结构：运行 `python3 -I -B scripts/storage_runtime.py contract`，并检查所有本地链接和命令。
- Web/UI：跑相关 API 测试和 tests/test_ui_e2e.py；若浏览器可用，再检查真实 localhost 页面、console、network 和核心路径。浏览器不可用时必须明确说明，不能把静态阅读当作浏览器验收。
- 默认或自动验收不得触发真实草稿写入。只有用户对独立 real 检查给出当次明确授权时才可创建测试草稿；任何验收都不得删除远端内容或触发最终发布。

测试和诊断产物必须写入 tmp_path、系统临时目录或被忽略的 artifacts/、reports/、outbox/；不得更新 tracked 报告或截图作为测试副作用。

## 关键目录

- src/wechat_article_scheduler/：业务代码、CLI、Web、调度和微信 adapter。
- tests/：pytest 测试。
- migrations/：已发布 SQLite 迁移；不得因代码清理删除历史迁移。
- articles/、content/collections/：用户内容与合集配置。
- docs/：少量当前文档；docs/backlog.md 只记录未来方向。
- scripts/：运维、结构检查和显式真实 API 检查。
- data/、storage/、outbox/、reports/、artifacts/：本地运行产物，不是源真相。

## 完成标准

- 主流程仍可导入、排期、创建/更新草稿、导出外部任务包并记录真实 proof。
- 默认 mock 未改变，最终发布调用在代码层不存在。
- 候选未新增测试失败，且没有测试向仓库写入运行产物。
- 未泄露秘密，未修改用户文章、本地数据库或会话。
- 删除的实现不存在残余导入、路由、CLI、UI、配置、测试或文档入口。
- 最终报告列出验证命令、结果、未验证项和仍保留的用户改动。
