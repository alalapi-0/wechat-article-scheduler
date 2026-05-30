# 数据库设计（SQLite）

## 当前表

1. `articles`：文章内容与状态
2. `publish_jobs`：发布任务与调度状态
3. `wechat_drafts`：草稿记录
4. `events`：审计日志

## 现状评估

- 已实现：基本 CRUD 与状态流转，适合本地单机 MVP
- 部分实现：`publish_jobs.retry_count` 通过轻量迁移新增
- 风险：事件 payload 无严格 schema；历史摘要长度存在漂移

## 演进建议

- 增加迁移版本表（如 `schema_migrations`）
- 为 `events` 约定字段级 JSON schema
- 为 `publish_jobs(status, scheduled_at)` 增加复合索引（按需）
