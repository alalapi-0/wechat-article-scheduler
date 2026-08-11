# Scheduler 常驻运行

Scheduler 根据本地 publish_jobs.scheduled_at 到点创建或更新草稿。它不会把时间写进微信后台，也没有最终发布能力。

同一数据库只能启用一个持续执行器：Web 自动执行、scheduler-daemon 或 cron 三选一。若使用 daemon 或 cron，请设置 WEB_AUTO_RUN_DUE=false，或不要同时运行 Web。手动 run-once 也应避开持续执行器正在处理任务的时刻。

## 模式

| 模式 | 行为 |
|---|---|
| WECHAT_MODE=mock | 默认，不联网，模拟草稿结果 |
| WECHAT_MODE=real | 调用真实素材/草稿 API；需要凭证和有效封面 |

任务会固定记录安排时的模式。若进程的 `WECHAT_MODE` 与任务模式不一致，调度器会记录 `adapter_mode_mismatch`、增加 `skipped_mode_mismatch`，并保持任务待执行；它不会自动把 mock 任务变成 real 任务。切换模式后，应在当前模式下重新安排任务。

先检查队列：

    .venv/bin/python -m wechat_article_scheduler.cli scheduler-health

单次执行：

    .venv/bin/python -m wechat_article_scheduler.cli run-once

前台常驻：

    .venv/bin/python -m wechat_article_scheduler.cli scheduler-daemon

包装脚本：

    bash scripts/run_scheduler_daemon.sh
    bash scripts/cron_run_once.sh

调度器有锁和 claim 恢复机制，但重复进程仍会造成无意义竞争。

## macOS launchd

先在仓库中执行 `mkdir -p data/logs`。把 deploy/examples/scheduler/com.wechat-article-scheduler.plist.example 复制为 ~/Library/LaunchAgents/com.wechat-article-scheduler.plist，并把 __REPO_ROOT__ 替换为仓库绝对路径。launchd 会在脚本启动前打开日志路径，因此该目录必须预先存在。示例默认 mock；本地 .env 中的 WECHAT_MODE 可覆盖它。

加载并启动：

    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.wechat-article-scheduler.plist
    launchctl kickstart -k gui/$(id -u)/com.wechat-article-scheduler

停止并卸载：

    launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.wechat-article-scheduler.plist

## Linux systemd

复制 deploy/examples/scheduler/wechat-article-scheduler.service.example 到 /etc/systemd/system/，修改用户、WorkingDirectory 和 EnvironmentFile，然后由用户执行 systemctl daemon-reload 和 systemctl enable --now。

## cron

参考 deploy/examples/scheduler/cron-run-once.example，每分钟调用一次 scripts/cron_run_once.sh。启用前关闭 Web 自动执行，并且不要同时启动 daemon。

## 诊断

    .venv/bin/python -m wechat_article_scheduler.cli scheduler-health
    .venv/bin/python -m wechat_article_scheduler.cli events --limit 30
    .venv/bin/python -m wechat_article_scheduler.cli retry-failed

| 现象 | 检查 |
|---|---|
| 到点未执行 | pending_due、进程/cron 是否运行、系统时区 |
| skipped_locked | 是否存在 Web 自动执行、另一个 scheduler 或 cron |
| stale_running | claim timeout 后是否自动恢复 |
| 反复失败 | events、封面路径、real 凭证与微信 API 错误 |
| 担心外部副作用 | 切回 WECHAT_MODE=mock，再用 dry-run 验证 |

日志位置由 LOG_FILE 控制，默认 data/logs/app.log。WEB_AUTO_RUN_DUE=true 时 Web 进程会处理勾选了 auto_execute 的到期任务；此时不要额外启动 daemon 或 cron。
