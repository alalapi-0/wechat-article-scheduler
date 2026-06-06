# Stitch 设计工作区

Stitch 是本项目的可选 UI 设计工具。它可生成 UI 原型、screen、variants、截图和 HTML，帮助 Agent 在改动 Web 工作台前先形成可评审的设计输入。

## 快速入口

- 配置：[`STITCH_MCP_SETUP.md`](STITCH_MCP_SETUP.md)
- 工作流：[`STITCH_WORKFLOW.md`](STITCH_WORKFLOW.md)
- 当前项目任务模板：[`UI_TASKS.md`](UI_TASKS.md)
- Prompt 模板：[`PROMPT_TEMPLATES.md`](PROMPT_TEMPLATES.md)
- 导出规范：[`EXPORT_GUIDE.md`](EXPORT_GUIDE.md)
- 全局设计约束：[`../DESIGN.md`](../DESIGN.md)

## 目录

```text
docs/design/stitch/
  exports/       # Stitch HTML、DESIGN.md、结构化导出
  screenshots/   # screen 与 variants 截图
  prompts/       # 实际使用过的 prompt
  reviews/       # 评审结论和实现任务拆分
```

生成物必须可追溯到任务和 prompt，文件名建议使用 `YYYYMMDD-页面名-版本`。任何导出代码都必须先评审，再按当前 `FastAPI + 原生 HTML/CSS/JS` 技术栈手工落地。

缺少 `STITCH_API_KEY` 或 MCP 不可用时，不阻塞文档与实现：记录原因，使用本目录模板完成设计说明，再进入浏览器验证。

参考：

- [Cursor MCP 配置文档](https://docs.cursor.com/zh/context/mcp)
- [Google Labs Stitch SDK](https://github.com/google-labs-code/stitch-sdk)
