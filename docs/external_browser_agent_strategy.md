# 外部 Browser Agent 策略

Status: Current lightweight boundary

## 为什么不内置浏览器 Agent

当前项目主线是微信公众号草稿与排期：读取本地文章、渲染公众号 HTML、上传封面、创建草稿、维护任务状态和 proof。浏览器后台操作只是辅助能力，不是核心能力。

如果在项目内部集成完整 Browser Assist / Browser Agent / LLM Agent，会额外引入：

- 大模型配置、API Key 管理和成本控制。
- 浏览器登录态、Cookie 和会话生命周期管理。
- 微信公众号后台页面识别、DOM selector 维护和误操作风险。
- 验证码、扫码登录、平台风控提示等高风险边界。
- 最终发布按钮误点、批量误操作和责任边界不清。

因此当前项目保持轻量更适合长期维护。项目只输出标准化、可审计、可人工检查的任务包；真正浏览器操作交给 Hermes、Cursor Agent、Playwright MCP、Browser Use 等成熟外部工具。

## 项目负责什么

- 本地文章扫描、去重、入库。
- Markdown / TXT / HTML 到公众号 HTML 渲染。
- 封面上传和微信公众号 API 草稿创建。
- 发布设置清单生成。
- 外部 Agent 操作提示词生成。
- `outbox/wechat_agent_tasks/` 任务 JSON、checklist、proof 模板导出。
- 用户回填 proof 后的本地记录。

## 外部 Agent 负责什么

- 打开微信公众号后台。
- 定位对应草稿。
- 核对标题、摘要、封面、正文排版。
- 辅助填写 API 无法覆盖的非最终字段。
- 截图或生成操作报告。
- 停在人机确认。

## 严格边界

- 不允许绕过验证码、扫码登录或平台风控。
- 不允许保存微信公众号后台 Cookie。
- 不允许保存微信账号密码。
- 不允许隐藏浏览器窗口执行不可见操作。
- 不允许默认点击最终发布。
- 外部 Agent 必须停在人类用户确认阶段。

