# 渲染器设计

## 目标

在发布前将输入文本稳定转换为公众号可接受 HTML，并保持可测试、可扩展。

## 当前状态

- 已实现：`renderers.markdown.render_markdown_to_html`
- 已实现：Markdown 段落渲染为带 margin 的 `<p>` 标签
- 未实现：标题映射、列表、图片、代码块与富文本白名单

## 规则基线

- 非 HTML 输入：按段落拆分并输出 `<p style="margin: 0 0 1em;">...`
- 已是 HTML 输入：原样透传
- digest 与正文渲染解耦，digest 单独 120 字裁剪

## 后续

- 逐步引入更完整 markdown 语义支持
- 增加微信内容规范校验器（链接、图片、注释等）
