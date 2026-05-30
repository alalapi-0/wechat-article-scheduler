# 渲染失败降级说明

1. **Web 预览**（`/api/articles/{id}/render-preview`）使用 `render_markdown_to_html_safe`：失败时仍返回转义后的段落 HTML，并在 JSON 中带 `render_error`。
2. **发布路径**（`RealWechatAdapter`）仍调用 `render_markdown_to_html`；异常会向上抛出，由调度/事件记录，不静默吞掉。
3. **HTML 正文**以 `<` 开头时跳过 Markdown 解析，避免破坏已有 HTML。
