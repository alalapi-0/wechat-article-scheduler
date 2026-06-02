# Browser Assist

Browser assist adapters must be human-in-the-loop and must not bypass captcha, QR login, risk controls, or click final publish automatically.

Current P0 scope is WeChat Official Account fallback only. Other platform browser_assist work is backlog and must not be implemented before the WeChat loop is stable.

## Round 18 / 25 交付

- 微信：`workflow.py` — `docs/browser_assist_runbook.md`
- 知乎评估（dry-run）：`zhihu_workflow.py` — `docs/zhihu_browser_assist.md`
- 豆瓣评估（dry-run）：`douban_workflow.py` — `docs/douban_browser_assist.md`
- Bilibili 评估（dry-run）：`bilibili_workflow.py` — `docs/bilibili_browser_assist.md`
- 统一入口：`plans.build_dry_run_plan(platform=...)`
- CLI：`browser-assist-plan --platform wechat_official|zhihu|douban|bilibili`
- Web：`/api/browser-assist-plan`、`/api/browser-assist/platforms`；`/debug` 含知乎评估 JSON

## 安全边界

- 不保存 password / cookie
- 不绕过验证码
- 状态止于 `awaiting_human_confirmation`，不默认 `published`
