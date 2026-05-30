# 开发轮次（Rounds）

机器可读状态：`governance/round_state.yaml`。推进前运行 `python scripts/agent_gate.py`。

| Round | ID | 目标 | 验收 |
|-------|-----|------|------|
| 0 | round_000 | SQLite、扫描、计划、mock 草稿、CLI | `pytest` + init-db/scan/plan/run-once 冒烟 |
| 1 | round_001 | 驳回流程、失败任务重试 | `reject` / `retry-failed` CLI + 测试 |
| 2 | round_002 | 事件查询与简单报告 | `events` CLI + 事件表测试 |
| 3 | round_003 | 真实 API 适配器骨架（默认仍 mock） | RealWechatAdapter token 占位 + 文档 |
| 4 | round_004 | 治理校验脚本与文档收尾 | `check_repo_contract.py` + 全量 pytest |
| 5 | round_005 | 真实微信 HTTP（token 缓存、素材、draft、发布） | `tests/test_real_adapter.py`（mock HTTP） |
| 6 | round_006 | FastAPI 管理后台 | `tests/test_web_app.py` + `serve` 命令 |
| 7 | round_007 | 加固：日志轮转、dry-run、重试上限、调度韧性 | `tests/test_scheduler_hardening.py` |

## Round 5

- `RealWechatAdapter`：`TokenCache`、`material/add_material`（thumb）、`draft/add`、`freepublish/submit`
- 仅 `WECHAT_MODE=real` 且凭证齐全时联网；单元测试 mock HTTP
- `WECHAT_ENABLE_PUBLISH=false` 可只建草稿不发布

## Round 6

- `wechat-scheduler serve` 启动 FastAPI
- 路由：文章列表、队列、事件、scan/plan/run-once 触发、mock 草稿预览

## Round 7

- `RotatingFileHandler` 日志（`LOG_FILE`）
- `DRY_RUN` 报告写入 `data/reports/dry_run_*.json`
- `MAX_JOB_RETRIES` 与 `retry_count` 列
- 调度循环连续异常退避

## Round 0–4（历史）

见 git 历史与各 `docs/reports/round_*_completion.md`。
