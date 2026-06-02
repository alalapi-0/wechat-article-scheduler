# 发布队列页面（Round 67 / 收敛 Round 12）

## 能力

- **筛选**：待发布 / 发布中 / 已完成 / 失败 / 全部（工作台「发布队列」区）
- **队列表格**：计划时间、发布配置、状态（含「已到点」标记）、失败原因（失败/全部筛选）
- **操作**：取消待发布、单条重试、重试全部失败、跳转作品详情
- **摘要**：`GET /api/queue-summary` 显示各状态计数

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/jobs?status=pending` | 队列行（含 `failure_reason`、`is_due_now`、`next_hint`） |
| GET | `/api/queue-summary` | 状态统计与到点数 |
| POST | `/api/jobs/{id}/retry` | 单条失败任务重试 |
| POST | `/api/jobs/bulk-retry` | `retry_all` 或 `job_ids` 批量重试 |

失败原因来自 `events` 表最近一条 `job_failed` 记录（人话载荷，无密钥）。

## 验证

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli serve
python -m pytest tests/test_publish_queue_page.py -q
```

浏览器：打开 `http://127.0.0.1:8080/#queue`，切换筛选 Tab，确认 `/api/jobs` 与 `/api/queue-summary` 返回 200。
