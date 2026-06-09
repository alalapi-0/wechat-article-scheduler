# browser_assist 操作清单（Round 18）

Status: Current — 与 `docs/wechat_browser_assist_strategy.md` 配套

## 适用场景

当 `wechat_field_matrix` 标记为 `unverified` / `partial` / `no`，且 `handling` 建议 **browser_assist + 人工确认** 时使用。典型字段：

- `cover_crop` — 封面裁剪效果需后台目视
- `wechat_backend_schedule` — API 不支持；Agent 可准备目标时间并保存草稿，最终发表由用户完成
- `show_cover_pic` — 封面是否显示在正文（API 待核验）

## 标准流程

1. **本地预检**：API 创建/更新草稿；记下 `article_id`、`media_id`。
2. **连接后台**：按 [`wechat_chrome_session_runbook.md`](wechat_chrome_session_runbook.md) 使用 `wechat-chrome-session --autoConnect` 接管用户已经登录的 Chrome 标签页。
3. **登录状态分流**：只根据可见页面、URL、标题、浏览器 snapshot 或用户确认判断，不读取 cookie/session/token。若已自动进入公众号后台（可见后台导航、首页、内容管理或草稿箱），直接进入内容管理/草稿箱继续；若仍在登录、二维码、验证码或风控页，等待用户扫码/验证后再继续。
4. **设置字段**：按 `target_fields` 设置合集、推荐/通知、封面显示和目标时间。
5. **保存与复查**：点击保存草稿，重新打开同一草稿，记录字段和目标时间是否持久化。
6. **人工处理**：最终发表、扫码/手机确认和管理员验证由用户本人完成。
7. **回填 proof**（Round 19）：截图路径、链接、确认人、时间 → 本地记录 `waiting_confirmation` 或 proof 状态；proof 不等于自动发布成功。

## 禁止项

- 保存密码、cookie、token
- 绕过验证码或扫码
- 自动最终发布、扫码代验或批量灌水
- 将未确认任务标为「已正式发布」

## 命令与 API

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan --article-id 1 --media-id MOCK_MEDIA_1
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-session start --job-id 1
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-session record-connection --session-id <id> --report-json '{"mcp":"wechat-chrome-session","target_host":"mp.weixin.qq.com","target_url":"https://mp.weixin.qq.com/cgi-bin/home","backend_visible":true,"login_required":false,"dom_snapshot_available":true,"screenshot_available":true,"write_actions_performed":0,"result":"PASS","block_reason":"none"}'
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-session confirm-login --session-id <id>
```

- Web：`GET /api/browser-assist-plan?article_id=&media_id=`
- Web 手动登录门控：`POST /api/browser-assist/sessions/start` → `record-connection`（记录接管现有已登录页报告）→ `confirm-login` → 草稿检查完成后记录 proof。历史 `confirm-schedule-setup` / `confirm-final-schedule` 入口仅作兼容别名，不代表已设置后台定时。
- 作品详情页：**浏览器辅助（手动登录）** 卡片
- Chrome 已登录会话：见 [`docs/wechat_chrome_session_runbook.md`](wechat_chrome_session_runbook.md)
- 高级排错：`/debug` 加载 JSON

## dry-run 实现

逻辑见 `src/wechat_article_scheduler/adapters/browser_assist/workflow.py` 的 `build_dry_run_plan()`。
