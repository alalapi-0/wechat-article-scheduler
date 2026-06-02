# 小红书 manual_export 发布包

Status: Round 32 / agent round_094（不真上传）

高风控平台：仅人工发布路径，导出包不含图片/视频二进制。

## 文件

| 文件 | 用途 |
|------|------|
| xhs_title.txt | 标题 |
| xhs_caption.txt | 短描述 |
| xhs_note_body.md | 笔记正文 |
| xhs_tags_hint.md | 话题提示 |
| xhs_cover_notes.txt | 封面说明 |
| xhs_media_placeholder.txt | 图集/视频占位 |
| xhs_publish_checklist.md | 发布清单 |
| xhs_publish.md | 总览 |

## CLI

```bash
python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform xiaohongshu
```

别名：`--platform xhs` 在 browser-assist 中支持；export 请用 `xiaohongshu`。
