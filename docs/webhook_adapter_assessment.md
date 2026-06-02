# Webhook 适配器评估

Status: agent round_089（dry-run，不发起 HTTP）

Webhook 用于「文章就绪 / 待人工发布」等**通知**，不能替代 `submit-proof` 的发布证明。

## 渠道

- `generic` — 通用 JSON
- `feishu` — 飞书机器人（需签名）
- `slack` — Incoming Webhook

## CLI / API

```bash
python -m wechat_article_scheduler.cli webhook-plan --channel generic
```

- `GET /api/webhook-plan?channel=generic`
- `GET /api/webhook/channels`

环境变量：`WEBHOOK_URL`（可选 `WEBHOOK_SECRET`）。
