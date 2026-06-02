# 真实 API 样本（Round 54）

`scripts/real_api_check.py` 默认读取本目录下 `*.md`（按文件名排序，最多 `--samples` 条）。

| 文件 | 用途 |
|------|------|
| `01_normal.md` | 正常短文 |
| `02_duplicate_title.md` | 标题与正文首行重复（发布时会去重） |
| `03_escaped_html.md` | 转义 HTML 源码（质量检查备注） |

样本 frontmatter 支持 `title`、`summary` 字段；正文为 Markdown。
