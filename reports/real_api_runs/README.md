# 真实 API 运行报告

`scripts/real_api_check.py` 每次运行写入 `run_YYYYMMDDTHHMMSSZ.json` 与同名 `.md`。

## 示例

- `run_20260531T230509Z.json` — 3 条样本 draft-only 成功（`enable_publish: false`）
- `run_20260531T230611Z.json` — 含渲染与转义 HTML 质量备注

报告不含 `access_token` / `secret` 明文；`media_id` 可能截断显示。

## 无凭证 / mock 模式

```bash
WECHAT_MODE=mock python3 scripts/real_api_check.py --dry-run --skip-if-blocked
```

仍落盘报告并记录 `blocking_reason`，退出码 0，供 Agent 门控不硬停。

## 真实验证（本地 `.env`，勿提交）

```bash
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python3 scripts/real_api_check.py --samples 3
```
