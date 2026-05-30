# 开发轮次（Rounds）

机器可读状态：`governance/round_state.yaml`。推进前运行 `python scripts/agent_gate.py`。

| Round | ID | 目标 | 验收 |
|-------|-----|------|------|
| 0 | round_000 | SQLite、扫描、计划、mock 草稿、CLI | `pytest` + init-db/scan/plan/run-once 冒烟 |
| 1 | round_001 | 驳回流程、失败任务重试 | `reject` / `retry-failed` CLI + 测试 |
| 2 | round_002 | 事件查询与简单报告 | `events` CLI + 事件表测试 |
| 3 | round_003 | 真实 API 适配器骨架（默认仍 mock） | RealWechatAdapter token 占位 + 文档 |
| 4 | round_004 | 治理校验脚本与文档收尾 | `check_repo_contract.py` + 全量 pytest |

## Round 0

- 目录：`articles/inbox|imported|published|rejected`
- 命令：`init-db`, `scan`, `plan`, `run-once`, `scheduler`
- `WECHAT_MODE=mock` 默认

## Round 1

- `reject --article-id N`：移至 rejected、取消 pending 任务
- `retry-failed`：将 failed 任务重置为 pending

## Round 2

- `events --limit N`：打印最近审计事件

## Round 3

- `RealWechatAdapter` 提供 `build_token_request_url()` 等占位，不默认联网
- 仅在 `WECHAT_MODE=real` 且配置 AppID/Secret 时尝试（仍可能 NotImplemented）

## Round 4

- 治理脚本与 `docs/reports/round_004_completion.md`
