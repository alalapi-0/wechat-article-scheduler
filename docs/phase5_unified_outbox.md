# Phase5 统一 outbox 预研（Round 41 / agent round_105）

Status: 只读索引与 manifest 汇总 dry-run；**不**移动文件，**不**标记已发布。

## 能力

| 组件 | 说明 |
|------|------|
| `config/unified_outbox.example.yaml` | 扫描根目录与 guardrails |
| `core/unified_outbox_presearch.py` | `outbox/` 包索引、按平台聚合、`projects` 内 publish_manifest 校验汇总 |
| CLI | `unified-outbox-dry-run` |
| API | `GET /api/unified-outbox/dry-run`、`GET /api/unified-outbox/index` |
| `/debug` | Phase5 统一 outbox 与 manifest 汇总 |

## 与现有 outbox

- `export-outbox` / `list_outbox_packages`：真实导出（会写目录）
- 本模块：预研级**只读**扫描，用于跨平台目录视图，不替代导出命令

## 微信主线

`articles/inbox` + `scan` + `plan` 不变；`outbox/` 与 `articles/` 分离。
