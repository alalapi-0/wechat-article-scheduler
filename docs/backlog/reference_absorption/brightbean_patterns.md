# BrightBean Studio 模式吸收

## 可吸收模式

- `Post + PlatformPost + PublishLog`：内容、平台任务、发布日志分层。
- 每个平台独立状态、错误、重试次数、`next_retry_at`。
- 审批与人工确认：适合无官方 API 或高风险平台。
- `PublishLog / attempt`：记录每一次尝试，而不只记录最终状态。
- `IdempotencyRecord`：防止重复请求造成双发。

## 本项目落点

- `publish_attempt` 表记录尝试。
- `review_record` 表记录人工决定。
- `proof_of_publish` 表记录链接、平台 ID、截图路径、备注。
- `idempotency_record` 表记录幂等响应快照。
- JSONL 镜像写入 `storage/logs/`，便于本地排障和备份。

## 不吸收

- 不照搬 BrightBean。
- 不引入 Django。
- 不做 Client Portal、Magic Link、多用户权限。
- 不把个人工具升级成商业协作系统。
