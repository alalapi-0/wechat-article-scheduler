# Search Policy

Date: 2026-06-09

## 必须搜索的情况

1. Cursor / Codex / MCP / Playwright / Browser / Chrome DevTools / GitHub CLI 能力或配置变更
2. 第三方库 API、框架配置、版本差异（FastAPI、Playwright、PyYAML 等）
3. 微信公众号草稿 API、字段限制、digest/标题长度
4. 平台发布规则、风控、自动化限制
5. AI 模型 API、价格、调用限制（本项目默认不调用）
6. 安全规则、合规要求
7. 报错无法仅凭本地代码判断
8. 用户明确要求「查一下」「搜索」「最新」

## 优先来源

1. 官方文档（如 developers.weixin.qq.com、fastapi.tiangolo.com、cursor.com/docs、developers.openai.com/codex）
2. 官方 changelog / release notes
3. 官方 GitHub 仓库
4. 标准文档（OpenAPI、MCP 规范）
5. 高质量技术博客（辅助）
6. 社区讨论（仅辅助，不作合规依据）

## 搜索结果处理

- 写入 `docs/RESEARCH_NOTES.md`
- 注明日期、关键词、来源类型、不确定性
- 官方文档与博客冲突时以官方为准
- 无法搜索时记录 `TOOL_UNAVAILABLE_WEB_SEARCH`

## 本项目高频查询

| 主题 | 官方入口 |
|------|----------|
| 微信草稿 API | https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add |
| FastAPI | https://fastapi.tiangolo.com/ |
| Cursor Agent | https://cursor.com/learn/customizing-agents |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md |
| Playwright Python | https://playwright.dev/python/ |
