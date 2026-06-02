# 摘要、错误码与草稿幂等（收敛 Phase 1 Round 3 / Round 58）

## 摘要 120 字

- 统一入口：`parser.clamp_summary(text, 120)`。
- 调度执行：`scheduler/domain.py` 在 `create_draft` 前对 title/summary 兜底截断。
- 真实适配器：`adapters/real.py` 的 `draft/add` 同样使用 `clamp_summary`。
- 超长时写入事件 `digest_truncated_warning`（见 `tests/test_digest_limits.py`）。

## 微信错误码

- 模块：`wechat_article_scheduler/wechat_errors.py`
- `WechatApiError` 携带 `human_hint`；任务失败事件 `job_failed` 使用 `format_job_failure`（不记录 token）。

| errcode | 说明摘要 |
|--------|----------|
| 40001 | access_token 无效或过期 |
| 42001 | access_token 超时 |
| 48001 | API 未授权 |
| 61451 | 草稿数据非法 |
| 85019 | 草稿数量达上限 |

## 草稿创建幂等

- 模块：`scheduler/draft_idempotency.py`
- 规则：同一 `article_id` + 未变的 `content_hash` 若已有 `wechat_drafts.status=created`，复用 `media_id`，不再调用 `create_draft`。
- 事件：`draft_idempotent_reuse`；统计字段 `draft_reused`（`run_due_jobs` 返回值）。

## 测试

```bash
.venv/bin/python -m pytest tests/test_digest_limits.py tests/test_wechat_digest_errors_idempotency.py tests/test_real_adapter.py -q
```
