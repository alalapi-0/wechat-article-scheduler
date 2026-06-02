# manual_export 操作说明（Phase 2 Round 23）

Status: Current — 文本平台低风险导出

## 用途

为无官方 API 或需人工复制的平台生成本地 **outbox** 目录，包含：

- `article.md` — Markdown
- `article.html` — 公众号风格 HTML
- `cover.*` — 封面（若有）
- `manifest.json` — 元数据
- `INSTRUCTIONS.md` — 复制说明

**不联网、不登录平台、不将作品标为已发布。**

## 命令

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli export-outbox --article-id 1
```

## Web

- 作品详情 →「导出 outbox 包」
- `GET /api/outbox-packages` — 最近导出列表
- `/debug` 可查看 JSON

## 与 proof

导出后请手动上传至目标平台，再在作品详情提交 **发布证明**；参见 `docs/proof_of_publish.md`。
