# Playwright MCP / browser_mcp 模式吸收

## 可吸收模式

- 浏览器只作为辅助层，不作为核心业务逻辑。
- 对无官方 API 的平台，使用 `browser_assist` 适配器类型。
- 适合生成操作说明、打开后台、辅助填表、截图、等待人工确认。
- 所有 browser_assist 任务必须进入 `waiting_confirmation`。
- 发布完成必须附加 `proof_of_publish`。

## 安全边界

- 不绕过验证码。
- 不绕过扫码登录。
- 不保存平台密码明文。
- 不保存公众号或其他平台后台 cookie。
- 不自动点击最终发布按钮。
- 不声称 browser_assist 已经支持某个平台，除非经过独立验证。

## 本项目落点

- `BrowserAssistAdapter.prepare(job)` 生成操作清单和 outbox。
- `publish(job)` 对 browser_assist 默认不可直接最终发布。
- `confirm(job, proof)` 在人工提交 proof 后更新状态。
- Web 控制台未来展示审核/确认队列、截图、proof 上传入口。

## 不吸收

- 不把浏览器自动化写入 scheduler 核心。
- 不让浏览器页面承担定时器职责。
- 不用自动化规避平台风控。
