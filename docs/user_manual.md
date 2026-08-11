# 用户手册

## 1. 初始化

    python3 -m venv .venv
    .venv/bin/python -m pip install -e ".[dev]"
    cp .env.example .env
    cp config/rules.example.yaml config/rules.yaml
    .venv/bin/python -m wechat_article_scheduler.cli init-db
    .venv/bin/python -m wechat_article_scheduler.cli serve

浏览器打开 http://127.0.0.1:8080/。工作台没有登录保护，只能在本机使用。

## 2. 导入文章和封面

推荐在 Web 工作台上传 Markdown、TXT 或 HTML。Markdown 可包含 title、summary 等 frontmatter。封面支持 JPG/JPEG 和 PNG；同名文件可以自动配对，也可以在文章详情中单独更换。

CLI 方式：把文章放入 articles/inbox/ 后执行：

    .venv/bin/python -m wechat_article_scheduler.cli scan

scan 会解析、按内容哈希去重、写入 SQLite，并把成功导入的文件移到 imported。重新上传曾软删除的同一内容会恢复该文章，而不是创建重复记录。

## 3. 排期并创建草稿

在工作台选择文章和时间，或执行：

    .venv/bin/python -m wechat_article_scheduler.cli plan
    .venv/bin/python -m wechat_article_scheduler.cli run-once

plan 只生成本地 publish_jobs。run-once 只处理已经到点的任务：mock 模式生成本地模拟草稿；real 模式创建或更新微信草稿。它不会把排期写入微信后台，也不会提交最终发布。

任务会固定记录安排时的 `mock` 或 `real` 模式。若运行进程的 `WECHAT_MODE` 与任务模式不一致，调度器会记录 `adapter_mode_mismatch` 并保持任务待执行，不会自动跨模式运行。需要切换模式时，请在当前模式下重新安排该任务。旧草稿若缺少可核验的任务和模式来源，也不会被跨模式更新、复用或用于发布 proof。

常驻运行见 [Scheduler 手册](scheduler_runbook.md)。Web 自动执行、scheduler-daemon 和 cron 只能启用一种。

## 4. 失败、回收站和更新

    .venv/bin/python -m wechat_article_scheduler.cli retry-failed
    .venv/bin/python -m wechat_article_scheduler.cli update-draft --article-id 1
    .venv/bin/python -m wechat_article_scheduler.cli events --limit 30

Web 队列可以重试失败任务或清除全部失败记录。清除操作只删除 publish_jobs 中 status=failed 的本地队列记录，不删除文章、草稿或事件。

文章删除采用本地软删除。用户文章正文和已发布内容不应由自动清理任务删除。

## 5. real 模式

在本地 .env 配置 WECHAT_MODE=real、WECHAT_APP_ID、WECHAT_APP_SECRET，并为文章绑定有效封面或设置 WECHAT_DEFAULT_THUMB_PATH。

real 模式会联网。缺少有效封面时，预检和 adapter 会在获取 token 或发送其他 HTTP 请求前失败。项目没有最终发布 API；real 模式仍然只创建/更新草稿或做只读同步。

先运行无网络 dry-run：

    .venv/bin/python scripts/real_api_check.py --dry-run --skip-if-blocked

真实草稿测试会产生外部副作用，只在用户明确授权后运行。

## 6. 只读同步远端草稿

    .venv/bin/python -m wechat_article_scheduler.cli sync-remote --dry-run
    .venv/bin/python -m wechat_article_scheduler.cli sync-remote

sync-remote 会通过 draft/batchget 分页读取公众号远端草稿。--dry-run 仍会调用只读微信接口，但不写本地数据库；正式同步只更新 SQLite 中的 remote_content_mirror，不修改或删除公众号内容。mock 模式用于本地演练，real 模式需要有效凭证和对应只读权限。

## 7. 外部 Agent 和 proof

草稿创建后可导出任务包：

    .venv/bin/python -m wechat_article_scheduler.cli export-agent-task --job-id 1
    .venv/bin/python -m wechat_article_scheduler.cli export-agent-tasks --status draft_created

任务包位于 outbox/wechat_agent_tasks/，包含脱敏任务、检查清单、文章预览和只读检查报告模板。外部 Agent 或人工只负责定位草稿、核对字段、截图和报告，并在最终发布前停止。该检查报告不能作为发布 proof。

用户完成后台操作后，可以先标记等待确认，再提交真实 proof：

    .venv/bin/python -m wechat_article_scheduler.cli mark-waiting-confirmation --job-id 1
    .venv/bin/python -m wechat_article_scheduler.cli submit-proof --job-id 1 --screenshot-path /path/to/actual-proof.png --confirmed-by user

proof 必须至少包含用户实际提供的公开 URL 或截图路径；备注只能补充说明，不能单独作为证据。项目不会生成占位 proof 冒充发布完成。
该流程只接受已经创建或复用真实微信草稿的 real 任务；mock 演练不能进入人工发布确认，也不能把文章标为已发布。

## 8. 本地内容位置

- articles/inbox/：待导入文章。
- articles/imported/：已导入文章文件。
- articles/published/：历史用户内容；当前调度器不会自动移动文章到这里。
- content/collections/：多合集配置和内容。
- data/app.sqlite3：本地数据库。
- storage/：预览等本地运行状态。
- outbox/、reports/、artifacts/：可再生成的本地产物，Git 忽略。
