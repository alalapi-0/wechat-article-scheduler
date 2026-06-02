# 渲染器设计

## 目标

在发布前将输入文本稳定转换为公众号可接受 HTML，并保持可测试、可扩展。

## 当前状态（Round 59）

- **发布与预览同源**：`renderers/wechat.py` + `publish_preview.render_for_publish`
- 支持：标题、段落、无序/有序列表、引用、围栏代码、链接、图片占位、粗体/斜体、内嵌 HTML（保守白名单）
- digest 与正文渲染解耦，digest 单独 120 字裁剪（`parser.clamp_summary`）
- 详见 [wechat_html_renderer.md](wechat_html_renderer.md)

## 规则基线

- 非 HTML 输入：走 `render_wechat_html`
- 已是完整 HTML 文档（以 `<` 开头且无 Markdown 标题行）：`markdown.py` 可原样透传；发布路径仍经 `publish_body_for` 归一化
- 不输出 `<script>` / 任意事件属性；`<a href>` 保留

## 后续（收敛路线图）

- Round 5：公众号效果预览快照
- 微信内容规范校验器（外链、图片域名等）
