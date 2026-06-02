# 本地 Scheduler 稳定化（Round 69 / 收敛 Round 14）

## 能力

| 能力 | 说明 |
|------|------|
| 原子 claim | `pending` → `running` 条件更新，避免重复执行 |
| 单实例锁 | `scheduler_locks` 表，`run-once` / `scheduler` 互斥 |
| 卡住恢复 | `running` 超过 `SCHEDULER_CLAIM_TIMEOUT_SECONDS`（默认 900s）恢复为 `pending` |
| 退避重试 | 失败后 `pending` + `next_retry_at`（60s / 5min / 30min），达 `MAX_JOB_RETRIES` 才 `failed` |
| misfire 记录 | 晚于计划时间超过 `SCHEDULER_MISFIRE_GRACE_MINUTES` 仍补发，并写 `job_misfire` 事件 |
| 健康检查 | `python -m wechat_article_scheduler.cli scheduler-health` |

## 常用命令（默认 mock）

```bash
python -m wechat_article_scheduler.cli run-once
python -m wechat_article_scheduler.cli scheduler
python -m wechat_article_scheduler.cli scheduler-health
python -m wechat_article_scheduler.cli retry-failed
```

## 环境变量

- `SCHEDULER_CLAIM_TIMEOUT_SECONDS`（默认 900）
- `SCHEDULER_LOCK_TTL_SECONDS`（默认 300）
- `SCHEDULER_MISFIRE_GRACE_MINUTES`（默认 60）
- `MAX_JOB_RETRIES`（默认 3）

## 验证

```bash
python -m pytest tests/test_scheduler_stability.py tests/test_scheduler_hardening.py -q
python scripts/agent_gate.py gate
```
