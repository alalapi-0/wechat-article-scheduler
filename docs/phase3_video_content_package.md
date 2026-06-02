# Phase 3 视频内容包预研

Status: Round 29 / agent round_090（dry-run，不上传）

## 最小视频内容包字段

| 字段 | 必填 | 说明 |
|------|------|------|
| video_path | 是 | 本地主视频路径 |
| cover_path | 是 | 封面图 |
| title | 是 | 标题 |
| description | 否 | 简介 |
| tags | 否 | 标签列表 |
| subtitle_path | 否 | 字幕文件 |

## 平台预研（占位）

- **bilibili**：优先 `manual_export` 上传包，其次 browser_assist 评估
- **wechat_channels**：仅 manual_export 字段设想
- **xiaohongshu**：延后，高风控

## CLI / API

```bash
python -m wechat_article_scheduler.cli video-package-plan --platform bilibili
```

- `GET /api/video-package-plan?platform=bilibili`
- `GET /api/video-package/platforms`

Registry 已登记占位能力，`implemented` 仍为 false。

## 边界

- 不改 `articles` 表结构
- `manifest` 中 `content_type=video` 需 `video_path`（round_090 校验扩展）
