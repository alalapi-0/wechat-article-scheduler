# Webhook

`eval_workflow.py` / `plans.py` 提供通知类 webhook 评估干跑（generic、feishu、slack）。默认不发起 HTTP；成功送达不等于平台已发布。

```bash
python -m wechat_article_scheduler.cli webhook-plan --channel generic
```

详见 `docs/webhook_adapter_assessment.md`。
