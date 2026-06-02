# Round 55 验证状态（Agent 记录）

## 门控策略

- **无微信凭证 / `WECHAT_MODE=mock`**：`pytest tests/test_auto_approve_pipeline.py` + `auto_approve_pipeline --dry-run --skip-downstream --skip-if-blocked`（exit 0，不硬停）。
- **有 `.env` 凭证**：`WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python3 scripts/auto_approve_pipeline.py --round 1 --samples 3`。

## 硬阻塞

缺少凭证时无法在 CI 自动创建 ≥3 条真实草稿；mock 工作台与 scan/run-once 仍可继续。

## 元数据

`real_api_check` 样本结果含 `review_status=auto_approved`（见 `scripts/real_api_check.py` `_auto_review_metadata`）。
