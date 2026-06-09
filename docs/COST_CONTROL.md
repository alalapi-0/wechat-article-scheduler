# Cost Control

本项目默认 **不产生 AI API 费用**。

## 开关

| 资源 | 默认 | 显式开启 |
|------|------|----------|
| 微信 API | mock | `WECHAT_MODE=real` + 本地凭证 |
| Stitch MCP | 未调用 | `STITCH_API_KEY` 环境变量 |
| Codex | 未使用 | 用户 Codex 订阅 |
| 真实发布 | 禁止 | 人工在公众号后台 |

## Agent 规则

- 不调用付费 LLM API
- Stitch 仅设计轮次且需记录是否使用
- `real_api_check.py` 默认 `--dry-run --skip-if-blocked`
- 成本相关操作写入 `tools_not_used` 或 `risks`

## Ledger（建议）

真实 API 运行报告目录：`reports/real_api_runs/`（已有）。
