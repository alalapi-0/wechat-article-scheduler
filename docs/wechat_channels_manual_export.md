# 微信视频号 manual_export 发布包

Status: Round 34 / agent round_096（不真上传）

视频号与**微信公众号 API**分离：本包仅供人工在「视频号助手」发表，不调用 `draft/add`。

## CLI

```bash
python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform wechat_channels
```

## 文件

- `channels_title.txt` / `channels_description.txt`
- `channels_video_placeholder.txt` — 视频需自备
- `channels_article_link_note.txt` — 与公众号关系说明
- `channels_publish_checklist.md`
