# 渲染规则矩阵（Round 13）

| 输入 | 行为 | 输出 |
|---|---|---|
| 空正文 | 返回空字符串 | `""` |
| 以 `<` 开头的 HTML | 原样返回，不二次解析 | 原始 HTML |
| 双换行段落 | 非列表/标题块 → `<p>` | 带 `margin` 的段落 |
| `#` / `##` / `###` 单行标题 | 映射 `h1`–`h3` | 带 margin 的标题 |
| `-` / `*` 列表块 | 连续列表行 → `<ul><li>` | 无序列表 |
| `[文本](url)` | 转义后生成 `<a href>` | 链接 |
| `![alt](url)` | 图片占位 `<span class="img-placeholder">` | 不拉取远程图 |
| 渲染异常 | `render_markdown_to_html_safe` | 转义段落 + `render_error` |

摘要/标题兜底见 `parser.py` 的 `make_summary` / `parse_file`（缺省用首标题或文件名）。
