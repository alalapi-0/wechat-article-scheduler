# Round 54 验证状态（Agent 记录）

## 门控策略

- **无 `WECHAT_APP_ID` / `WECHAT_APP_SECRET` 或 `WECHAT_MODE≠real`**：`agent_gate` 仅跑 `tests/test_real_api_check.py`（不联网）；`real_api_check --skip-if-blocked` 写报告后 exit 0。
- **有本地 `.env` 凭证**：可人工执行 `WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python3 scripts/real_api_check.py --samples 3` 完成 3 条草稿样本（勿提交 `.env`、勿打印 secret）。

## 硬阻塞（不停止 mock 主线）

缺少微信凭证时，**真实 draft/add 无法在 CI 自动执行**；mock 工作台、`run_due`、pytest 门控仍可推进 Round 55+。

## 参考报告

仓库内示例：`reports/real_api_runs/run_20260531T230509Z.*`
