# Bilibili browser_assist 评估

Status: Round 31 / agent round_093（dry-run）

配合 `export-outbox --platform bilibili` 使用；仅步骤与检查点，不自动投稿。

```bash
python -m wechat_article_scheduler.cli browser-assist-plan --platform bilibili
```

`GET /api/browser-assist-plan?platform=bilibili`
