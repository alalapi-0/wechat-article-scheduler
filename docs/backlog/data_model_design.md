# 数据模型设计

Status: Backlog / Not current development target

## 当前表结构记录

当前 SQLite 由 `src/wechat_article_scheduler/db.py` 初始化，并通过 `migrations/001..008` 演进。

- `schema_migrations`：迁移版本记录。
- `articles`：当前微信公众号文章主表，含标题、摘要、正文、hash、状态、封面、集合、软删除等字段。
- `publish_jobs`：当前微信发布任务表，含文章、计划时间、状态、adapter mode、重试次数、任务级发布配置。
- `wechat_drafts`：微信草稿记录，保存 `media_id` 与响应快照。
- `events`：系统事件审计。
- `collections/tags/article_tags`：内容库辅助表。

当前表不要直接破坏。未来新增表必须通过迁移逐轮落地，并保留旧 CLI 行为。

## 未来长期模型

### 1. project_profile

用途：记录每个本地创作项目。

字段建议：`id`、`project_id`、`root_path`、`display_name`、`default_timezone`、`content_type`、`tags_json`、`enabled`、`created_at`、`updated_at`。

### 2. publish_manifest_import

用途：记录每次从 manifest 导入的内容。

字段建议：`id`、`schema_version`、`project_id`、`manifest_path`、`package_id`、`manifest_hash`、`imported_at`、`status`、`error_message`。

### 3. content_package

用途：一次标准发布内容包。

字段建议：`id`、`project_id`、`package_id`、`title`、`summary`、`canonical_text_path`、`canonical_text_hash`、`content_type`、`lifecycle`、`metadata_json`、`created_at`、`updated_at`。

`lifecycle`：`draft`、`ready`、`locked`、`archived`。

### 4. media_asset

用途：统一管理图片、封面、视频、音频。

字段建议：`id`、`project_id`、`sha256`、`original_path`、`cached_path`、`role`、`mime_type`、`width`、`height`、`duration`、`size_bytes`、`variants_json`、`created_at`。

`role`：`cover`、`inline_image`、`video`、`audio`、`subtitle`、`attachment`。

### 5. platform_profile

用途：记录平台规则和能力。

字段建议：`id`、`platform`、`adapter_type`、`constraints_json`、`capability_json`、`enabled`、`created_at`、`updated_at`。

### 6. platform_account

用途：记录本地平台账号。

字段建议：`id`、`platform`、`display_name`、`account_key`、`adapter_type`、`credentials_ref`、`enabled`、`safety_mode`、`created_at`、`updated_at`。

`safety_mode`：`mock`、`draft_only`、`manual_only`、`real_publish`。

### 7. platform_payload

用途：每个平台的发布变体。

字段建议：`id`、`content_package_id`、`platform_account_id`、`title`、`caption`、`body_path`、`media_asset_ids_json`、`content_type`、`extra_json`、`payload_hash`、`validation_status`、`validation_report_json`、`created_at`、`updated_at`。

### 8. publish_job

用途：真正的调度任务。

字段建议：`id`、`content_package_id`、`platform_payload_id`、`platform_account_id`、`status`、`schedule_state`、`scheduled_at`、`claimed_at`、`claim_token`、`retry_count`、`next_retry_at`、`last_error`、`idempotency_key`、`content_fingerprint`、`created_at`、`updated_at`。

`status`：`draft`、`ready`、`scheduled`、`waiting_confirmation`、`publishing`、`published`、`failed`、`retry_waiting`、`cancelled`、`skipped`。

`schedule_state`：`pending`、`claimed`、`processed`、`misfired`、`paused`。

### 9. publish_attempt

用途：每次发布尝试。

字段建议：`id`、`publish_job_id`、`attempt_number`、`adapter_type`、`started_at`、`finished_at`、`duration_ms`、`status`、`http_status`、`platform_error_code`、`error_message`、`request_excerpt_json`、`response_excerpt_json`、`created_at`。

### 10. review_record

用途：人工审核或确认记录。

字段建议：`id`、`publish_job_id`、`reviewer`、`decision`、`comment`、`created_at`。

`decision`：`approved`、`rejected`、`changes_requested`。

### 11. proof_of_publish

用途：人工确认发布结果。

字段建议：`id`、`publish_job_id`、`platform_post_id`、`public_url`、`screenshot_path`、`submitted_by`、`submitted_at`、`note`。

### 12. idempotency_record

用途：防止重复操作。

字段建议：`id`、`idempotency_key`、`request_fingerprint`、`response_snapshot_json`、`expires_at`、`created_at`。

### 13. events

保留当前 `events` 思路，但明确它与 `publish_attempt` 的区别。

- `events` 记录系统事件：扫描、导入、排期、用户操作、状态变化。
- `publish_attempt` 记录发布尝试：请求、响应、耗时、错误码、适配器类型。

## 迁移原则

- 不修改旧表语义来伪装新模型。
- 新表先加只读导入和 dry-run，再接入写路径。
- 每轮迁移都必须有测试、回滚说明和旧 CLI 回归。
