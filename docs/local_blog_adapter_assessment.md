# 个人博客 / WordPress local_blog 评估

Status: Round 28 / agent round_088（dry-run，不真发）

## 结论摘要

| 目的地 | 推荐度 | 风险 |
|--------|--------|------|
| static_site | 推荐 | 低 |
| local_files | 推荐 | 低 |
| wordpress | 有条件 | 中 |

优先 **静态站 Markdown** 或 **本地目录**；WordPress REST 需凭证与人工确认草稿，不作为默认无人值守路径。

## CLI / API

```bash
python -m wechat_article_scheduler.cli local-blog-plan --destination static_site
python -m wechat_article_scheduler.cli local-blog-plan --destination wordpress
```

- `GET /api/local-blog-plan?destination=static_site`
- `GET /api/local-blog/destinations`

## 边界

- dry-run 不写入文件、不调用 WordPress API。
- 微信公众号 `scan/plan` 仍为 P0 主线。
