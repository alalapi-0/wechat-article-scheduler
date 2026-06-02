# Phase5 跨项目发布日历预研（Round 40 / agent round_104）

Status: dry-run 聚合与冲突检测；**不**写入 SQLite，**不**替代微信 `plan`。

## 能力

| 组件 | 说明 |
|------|------|
| `core/cross_project_calendar.py` | 从 `projects.yaml` 所列 manifest 的 `targets[].scheduled_at` 聚合日历视图 |
| 冲突检测 | `same_slot_same_account`（错误）、`min_gap_violation`（警告，默认 60 分钟） |
| CLI | `publish-calendar-dry-run` |
| API | `GET /api/publish-calendar/dry-run`、`GET /api/publish-calendar/conflicts` |
| `/debug` | Phase5 跨项目日历与冲突 JSON |

## 与 round_103

round_103 提供多项目 manifest 注册表；本模块在其上只读聚合排期，不导入 `publish_jobs`。

## 微信主线

`articles/inbox` + `scan` + `plan` + `run-once` 不变；日历数据来自 manifest 预研路径。
