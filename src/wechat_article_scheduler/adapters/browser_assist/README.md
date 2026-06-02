# Browser Assist

Browser assist adapters must be human-in-the-loop and must not bypass captcha, QR login, risk controls, or click final publish automatically.

Current P0 scope is WeChat Official Account fallback only. Other platform browser_assist work is backlog and must not be implemented before the WeChat loop is stable.

## Round 18 交付

- 流程文档：`docs/browser_assist_runbook.md`、`docs/wechat_browser_assist_strategy.md`
- 干跑骨架：`workflow.build_dry_run_plan()` — 操作清单、人工确认点、guardrails
- CLI：`browser-assist-plan`；Web：`/api/browser-assist-plan`

## 安全边界

- 不保存 password / cookie
- 不绕过验证码
- 状态止于 `awaiting_human_confirmation`，不默认 `published`
