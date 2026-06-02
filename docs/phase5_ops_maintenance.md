# Phase5 长期运维预研（Round 42 / agent round_106）

Status: runbook 检查清单 + 健康指标 dry-run；**不**安装或修改生产 cron/launchd。

## 能力

| 组件 | 说明 |
|------|------|
| `config/ops_maintenance.example.yaml` | 检查项与 guardrails |
| `core/ops_health_presearch.py` | 聚合 scheduler-health、DB、inbox、outbox、日志配置 |
| CLI | `ops-health-dry-run` |
| API | `GET /api/ops/health-dry-run`、`GET /api/ops/runbook-checklist` |
| `/debug` | Phase5 运维与 runbook JSON |

## 参考

- 调度常驻：`docs/scheduler_runbook.md`
- 部署样例：`deploy/examples/scheduler/`（只读对照，不自动安装）

## 微信主线

不改变 `scan` / `plan` / `run-once` 行为。
