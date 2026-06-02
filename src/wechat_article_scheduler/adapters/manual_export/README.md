# Manual Export

生成本地 **outbox** 发布包（Markdown、HTML、封面、manifest、说明）。不联网、不登录平台、**不**将作品标为已发布。

## 入口

- CLI：`export-outbox --article-id N [--platform zhihu|douban|bilibili|xiaohongshu|wechat_channels|douyin|kuaishou|generic]`
- Web：作品详情「导出 outbox 包」、`GET /api/outbox-packages`
- 代码：`adapters.manual_export.export_article_to_outbox`

人工发布后须在作品详情提交 **proof**（见 `docs/proof_of_publish.md`）。

详见 `docs/manual_export_runbook.md` 与 `docs/phase2_text_platforms.md`。
