# 调度与队列设计

## 现状

当前调度器支持单进程轮询、到期任务执行、失败重试计数和 Web 后台到点自动执行。Round 69 已落地：**原子 claim**、`scheduler_locks` 单实例锁、**stale running 恢复**、**next_retry_at 退避**、**misfire 事件** 与 `scheduler-health` CLI（详见 `docs/scheduler_stability.md`）。`publish_jobs.status` 仍承担发布状态与队列状态两种含义；`schedule_state` 分列仍为后续演进。

## 1. 到期任务原子 claim

未来执行到期任务时必须先 claim：

```sql
UPDATE publish_job
SET schedule_state = 'claimed', claimed_at = datetime('now'), claim_token = ?
WHERE id = ?
  AND schedule_state = 'pending'
  AND status IN ('ready', 'scheduled', 'retry_waiting')
  AND scheduled_at <= datetime('now');
```

只有受影响行数为 1 的 worker 才能执行任务。

## 2. SQLite 下防重复 claim

- 使用单条条件 `UPDATE` 抢占。
- claim 后立即提交事务。
- 执行完成时必须校验 `claim_token`。
- 超时 claim 可由恢复任务重置，但必须记录事件。

## 3. `schedule_state` 与 `status` 分离

- `status` 表示业务发布状态：`scheduled/publishing/published/failed/waiting_confirmation`。
- `schedule_state` 表示队列处理状态：`pending/claimed/processed/misfired/paused`。

## 4. `retry_waiting` 与 `next_retry_at`

失败后不应立即重复执行，应进入 `retry_waiting` 并写 `next_retry_at`。

## 5. 退避策略

- 第一次失败：1 分钟。
- 第二次失败：5 分钟。
- 第三次失败：30 分钟。
- 超过上限：`failed`。

## 6. misfire 策略

错过计划时间时按平台和任务配置处理：

- 可补发：进入 `pending` 并记录 misfire 事件。
- 需要人工确认：进入 `waiting_confirmation`。
- 允许跳过：标记 `skipped`。

高风险平台和 browser_assist 默认需要人工确认。

## 7. 单实例 scheduler 锁

本地模式先使用 SQLite 锁表或锁文件，避免同时启动两个 scheduler。锁必须有超时和持有者信息。

## 8. 本地运行方式

- CLI：`python -m wechat_article_scheduler.cli scheduler` / `scheduler-daemon`。
- 手动：`python -m wechat_article_scheduler.cli run-once`。
- 默认 mock 或 draft-only。
- **常驻部署**（launchd / systemd / cron / tmux）：见 `docs/scheduler_runbook.md` 与 `deploy/examples/scheduler/`。

## 9. Web 控制台运行方式

Web 页面可以触发 scan/plan/run-once，也可以启动后台轮询，但浏览器页面本身不是 scheduler 本体。

## 10. macOS launchd

未来提供 plist 示例，执行 CLI scheduler，并把日志写入本地文件。

## 11. Linux systemd

未来提供 service 示例，配置工作目录、环境文件、重启策略。

## 12. VPS 常驻

VPS 是后续部署选项，不是第一阶段默认目标。必须先解决备份、日志轮转、安全开关和健康检查。

## 13. 不依赖浏览器页面计时

调度必须在后端进程或 CLI 中运行，不依赖用户浏览器标签页保持打开。

## 14. 浏览器页面只是控制台

Web 控制台只展示队列、状态、预检和人工操作入口，不承担核心定时执行职责。
