# Bilibili manual_export 发布包

Status: Round 30 / agent round_092（不真上传）

## 导出文件

| 文件 | 用途 |
|------|------|
| bilibili_title.txt | 投稿标题 |
| bilibili_description.txt | 简介 |
| bilibili_body_supplement.md | 长文备稿（可选） |
| bilibili_tags_hint.md | 分区/标签提示 |
| bilibili_cover_notes.txt | 封面说明 |
| bilibili_video_placeholder.txt | 视频文件占位说明 |
| bilibili_upload_checklist.md | 人工上传清单 |
| bilibili_publish.md | 总览 |

另含通用 `article.md` / `article.html`（由 outbox 主流程生成）。

## CLI

```bash
python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform bilibili
```

## 边界

- 不包含视频二进制；用户自备 `video.mp4`
- 导出成功 ≠ 已发布；需 proof
