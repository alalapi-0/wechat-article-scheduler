# 抖音 / 快手发布包预研

Status: Round 35 / agent round_098–099（deferred，不真上传）

## 评估结论

| 平台 | recommendation | 说明 |
|------|----------------|------|
| 抖音 | deferred | 高风控；仅 `export-outbox --platform douyin` 骨架 |
| 快手 | deferred | 同上，`--platform kuaishou` |

不实现 browser_assist 自动投稿；不登录、不上传视频。

## CLI

```bash
python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform douyin
python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform kuaishou
python -m wechat_article_scheduler.cli short-video-plan --platform douyin
```

## API

- `GET /api/short-video-plan?platform=douyin`
- `GET /api/short-video/platforms`
