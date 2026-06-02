# Scheduler 常驻运行手册（Round 70 / 收敛 Round 15）

个人本地长期跑发布调度：**不依赖浏览器标签页**，由 CLI 进程或系统定时任务执行 `run-once` / `scheduler`。

## 模式说明（必读）

| 模式 | 环境 | 行为 |
|------|------|------|
| **演练（默认）** | `WECHAT_MODE=mock` | 不联网，模拟草稿/发布 |
| **真实草稿** | `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH=false` | 真实 API 仅创建草稿 |
| **真实发布** | `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH=true` | 到点可真正发文，需二次确认（Web） |

常驻 scheduler **不会**把定时写进公众号后台；仍是本地 `publish_jobs.scheduled_at` 到点后调用 API。详见 `docs/scheduler_stability.md`。

## 快速命令

```bash
# 项目根目录，已配置 .env
export WECHAT_MODE=mock   # 默认；真实 API 测试再改 real

python -m wechat_article_scheduler.cli scheduler-health
python -m wechat_article_scheduler.cli run-once          # 单次扫到期任务
python -m wechat_article_scheduler.cli scheduler        # 前台轮询（Ctrl+C 停止）
python -m wechat_article_scheduler.cli scheduler-daemon # 同 scheduler，带启动说明
bash scripts/run_scheduler_daemon.sh                    # 包装脚本（推荐 launchd/systemd 调用）
bash scripts/cron_run_once.sh                           # 仅适合 cron 每分钟触发一次
```

日志默认写入 `LOG_FILE`（见 `.env`，通常 `data/logs/app.log`），轮转由 `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` 控制。

## 方式一：前台 / tmux（最简单）

```bash
cd /path/to/wechat-article-scheduler
source .venv/bin/activate
export WECHAT_MODE=mock
python -m wechat_article_scheduler.cli scheduler
```

**tmux 示例**（断开 SSH 仍运行）：

```bash
tmux new -s wechat-sched
cd /path/to/wechat-article-scheduler && source .venv/bin/activate
export WECHAT_MODE=mock
python -m wechat_article_scheduler.cli scheduler
# 分离：Ctrl+B 然后 D；恢复：tmux attach -t wechat-sched
# 停止：attach 后 Ctrl+C
```

## 方式二：macOS launchd

1. 复制并编辑示例：

```bash
cp deploy/examples/scheduler/com.wechat-article-scheduler.plist.example \
   ~/Library/LaunchAgents/com.wechat-article-scheduler.plist
# 将 __REPO_ROOT__ 替换为仓库绝对路径
```

2. 加载 / 停止：

```bash
launchctl load ~/Library/LaunchAgents/com.wechat-article-scheduler.plist
launchctl start com.wechat-article-scheduler
launchctl stop com.wechat-article-scheduler
launchctl unload ~/Library/LaunchAgents/com.wechat-article-scheduler.plist
```

3. 日志：`deploy/examples/scheduler` 中 plist 将 stdout/stderr 指向 `data/logs/scheduler.launchd.log`。

**注意**：同一时刻不要同时跑 launchd `scheduler` 与 cron `run-once`，会争用 `run_once` 锁（见稳定化文档）。

## 方式三：Linux systemd

```bash
sudo cp deploy/examples/scheduler/wechat-article-scheduler.service.example \
  /etc/systemd/system/wechat-article-scheduler.service
# 编辑 User=、WorkingDirectory=、EnvironmentFile=
sudo systemctl daemon-reload
sudo systemctl enable --now wechat-article-scheduler
sudo systemctl status wechat-article-scheduler
sudo systemctl stop wechat-article-scheduler
```

日志：`journalctl -u wechat-article-scheduler -f`

## 方式四：cron（仅 run-once）

适合「每分钟扫一次到期任务」，**不要**与常驻 `scheduler` 双开。

```bash
crontab -e
# 参考 deploy/examples/scheduler/cron-run-once.example
```

示例行（需改路径）：

```
* * * * * /path/to/wechat-article-scheduler/scripts/cron_run_once.sh >> /path/to/wechat-article-scheduler/data/logs/cron.log 2>&1
```

## 健康检查与故障处理

| 现象 | 处理 |
|------|------|
| 任务不到点执行 | `scheduler-health` 看 `pending_due`；确认进程在跑或 cron 有执行 |
| `skipped_locked` | 另一实例占用锁；停掉重复 scheduler/cron |
| 任务卡在「发布中」 | 等待 `SCHEDULER_CLAIM_TIMEOUT_SECONDS` 自动恢复，或 `scheduler-health` 看 `stale_running` |
| 失败反复 | `retry-failed` 或 Web 队列重试；查看 `events` / `job_retry_scheduled` |
| 真实误发顾虑 | 保持 `WECHAT_MODE=mock` 或 `WECHAT_ENABLE_PUBLISH=false` |

```bash
python -m wechat_article_scheduler.cli scheduler-health
python -m wechat_article_scheduler.cli events --limit 30
python -m wechat_article_scheduler.cli retry-failed
```

## 与 Web 工作台的关系

- Web `serve` 可开启「到点自动执行」（`WEB_AUTO_RUN_DUE`），与 CLI scheduler **二选一** 即可，避免重复跑。
- 浏览器页面不是 scheduler 本体；关页不影响 CLI/launchd 调度。

## 示例文件索引

| 文件 | 用途 |
|------|------|
| `deploy/examples/scheduler/com.wechat-article-scheduler.plist.example` | macOS launchd |
| `deploy/examples/scheduler/wechat-article-scheduler.service.example` | systemd unit |
| `deploy/examples/scheduler/cron-run-once.example` | crontab 片段 |
| `scripts/run_scheduler_daemon.sh` | 守护进程入口（供 plist/service 调用） |
| `scripts/cron_run_once.sh` | cron 单次 run-once |
