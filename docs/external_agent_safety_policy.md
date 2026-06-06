# 外部 Agent 安全策略

Status: Mandatory boundary

## 默认关闭

- 默认不启用任何浏览器自动化。
- 默认不启用项目内部外部 Agent 调用。
- 默认不启用真实发布。
- 当前项目不内置 Hermes、Browser Use、Playwright MCP 服务或 LLM Agent。

## 允许外部 Agent 做

- `open_backend`
- `locate_draft`
- `compare_title`
- `compare_digest`
- `compare_cover`
- `compare_article_body`
- `check_comment_setting`
- `check_schedule_setting`
- `check_collection_setting`
- `fill_non_final_field`
- `take_screenshot`
- `generate_report`

## 禁止外部 Agent 做

- `bypass_login`
- `bypass_qr_scan`
- `bypass_captcha`
- `save_cookie`
- `read_password`
- `change_account_security_settings`
- `delete_draft`
- `delete_article`
- `mass_publish`
- `click_final_publish_without_user_confirmation`
- `hide_browser_window`
- `ignore_platform_warning`

## 需要人工确认的动作

- `final_publish`
- `delete_draft`
- `modify_existing_draft`
- `change_scheduled_time`
- `change_comment_policy`
- `change_collection`
- `submit_for_publish`

## proof 要求

外部 Agent 完成后，需要用户手动回填 proof。proof 可以是截图、后台状态描述、发布链接或草稿确认结果。没有 proof 的任务不能标记为已完成。

## 敏感信息

任务包不得包含 access token、AppSecret、公众号后台 Cookie、微信账号密码或 LLM API Key。所有疑似敏感信息必须脱敏。

