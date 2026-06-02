# 知乎发布包（Round 24）

Status: Current — manual_export `platform=zhihu`

## 导出

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli export-outbox --article-id 1 --platform zhihu
```

Web：作品详情 →「导出知乎包」。

## 目录内容

| 文件 | 用途 |
|------|------|
| `zhihu_title.txt` | 粘贴到知乎标题 |
| `zhihu_excerpt.txt` | 导语/摘要 |
| `zhihu_body.md` | 正文 Markdown |
| `zhihu_cover_notes.txt` | 封面说明 |
| `zhihu_publish_checklist.md` | 人工发布清单 |
| `zhihu_publish.md` | 汇总参考 |
| `article.md` / `article.html` | 通用稿 |
| `manifest.json` | 元数据 |

## 约束

- 不登录知乎、不自动发布
- 导出后须在作品详情提交 **proof** 方可标为已发布
