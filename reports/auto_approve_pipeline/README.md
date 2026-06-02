# Auto-Approved Real API Pipeline 报告

`scripts/auto_approve_pipeline.py` 每轮写入 `round_NN_YYYYMMDDTHHMMSSZ.json` 与同名 `.md`。

## 示例

- `example_round_01.json` — mock/无凭证时的结构示例（`auto_approve_enabled: true`，`mock: true`）

## 无凭证 / mock（Agent 门控）

```bash
python3 scripts/auto_approve_pipeline.py --round 1 --samples 3 \
  --skip-downstream --dry-run --skip-if-blocked
```

仍写入本目录与 `reports/real_api_runs/`，退出码 0。

## 真实验证（本地 `.env`，勿提交）

```bash
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false \
  python3 scripts/auto_approve_pipeline.py --round 1 --samples 3
```

人工模式：`REVIEW_MODE=manual` 且 `AUTO_APPROVE_GENERATIONS=false`。
