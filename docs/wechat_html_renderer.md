# Markdown 到微信公众号 HTML 渲染器（收敛 Phase 1 Round 4 / Round 59）

## 单一真相来源

| 用途 | 入口 |
|------|------|
| Web/API 预览 | `publish_preview.build_publish_preview` → `render_wechat_html_safe` |
| 草稿 `content` | `publish_preview.render_for_publish` → `render_wechat_html` |
| mock/real adapter | `create_draft` 内调用 `render_for_publish` |

预览 HTML 与 `draft/add` 字段 **同源**，发布前会先 `publish_body_for` 去掉与标题重复的首行 `# 标题`。

## 支持语法

- 标题 `#` ~ `######` → 带字号的 `<p style="...">`（不用 `<h1>`，兼容微信编辑器）
- 段落、软换行（段内 `<br/>`）
- 无序列表 `-` / `*`
- 有序列表 `1.`
- 引用 `>`
- 围栏代码块 ` ``` `
- 链接 `[text](url)`、图片占位 `![alt](url)`
- 粗体 `**`、斜体 `*`
- 内嵌 HTML 块（`<p>...</p>` 等）：保留 `<a>`，其余转义；`font-size:0` 段落转为 `<br/>` 间距

## 模块

- 实现：`src/wechat_article_scheduler/renderers/wechat.py`
- 旧版通用 Markdown：`renderers/markdown.py`（CLI/解析测试用，**发布路径不用**）

## 测试

```bash
.venv/bin/python -m pytest tests/test_wechat_renderer.py tests/test_publish_preview.py -q
```

Fixtures：`tests/fixtures/wechat_render_round4.md`
