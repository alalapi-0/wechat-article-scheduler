# 外部 Agent 任务包设计

Status: Current task package contract

## 目录结构

```text
outbox/
  wechat_agent_tasks/
    job-000001/
      task.json
      browser_agent_prompt.md
      checklist.md
      article_preview.html
      article_source.md
      cover.png
      metadata.json
      proof_template.md
```

封面源文件不是 PNG 时，导出器会保留原始后缀，例如 `cover.jpg`；`metadata.json` 会记录实际文件名。

## 文件说明

- `task.json`：机器可读任务，包含 job、article、草稿线索、允许动作、禁止动作和人工确认要求。
- `browser_agent_prompt.md`：给 Hermes / Cursor Agent / Playwright MCP / Browser Use 的自然语言操作提示。
- `checklist.md`：人工检查清单，确保标题、摘要、封面、正文、留言、合集、定时设置被核对。
- `article_preview.html`：本地渲染后的公众号 HTML 预览，用于对照后台排版。
- `article_source.md`：原始文章或数据库中清洗后的正文。
- `cover.png` / `cover.jpg`：封面文件。
- `metadata.json`：标题、摘要、作者、计划时间、留言设置、原文链接、合集等设置项。
- `proof_template.md`：外部 Agent 或用户完成后填写的证明模板。

## task.json 关键字段

- `task_type`: `wechat_official_draft_external_agent_assist`
- `job_id`
- `article_id`
- `title`
- `draft_id`
- `media_id`
- `scheduled_at`
- `author`
- `digest`
- `comment_setting`
- `collection_name`
- `content_source_url`
- `required_actions`
- `forbidden_actions`
- `manual_confirmation_required`
- `proof_required`
- `human_confirmation`

## 默认动作清单

允许外部 Agent 做：

- `open_backend`
- `locate_draft`
- `compare_title`
- `compare_digest`
- `compare_cover`
- `compare_article_body`
- `check_comment_setting`
- `record_manual_backend_publish_steps`
- `check_collection_setting`
- `report_non_api_field_gap`
- `take_screenshot`
- `generate_report`

禁止外部 Agent 做：

- `bypass_login`
- `bypass_qr_scan`
- `bypass_captcha`
- `save_cookie`
- `read_password`
- `change_account_security_settings`
- `delete_draft`
- `delete_article`
- `operate_outside_approved_manifest`
- `schedule_without_user_confirmation`
- `click_final_schedule_confirm`
- `click_final_publish_without_user_confirmation`
- `hide_browser_window`
- `ignore_platform_warning`

## 脱敏规则

任务包禁止写入以下敏感值：

- `WECHAT_APP_SECRET`
- `WECHAT_ACCESS_TOKEN`
- `WECHAT_TOKEN`
- `WECHAT_ENCODING_AES_KEY`
- `COOKIE`
- `SESSION`
- `AUTHORIZATION`
- `LLM_API_KEY`
- `OPENAI_API_KEY`

任务包可以包含草稿标题、计划草稿创建时间、人工后台发布清单、检查清单和本地预览文件路径。`media_id` 仅用于本地对照，不包含访问权限；实际后台定位优先使用标题。
