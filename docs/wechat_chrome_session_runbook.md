# 已登录 Chrome 只读连接

这是可选的外部浏览器协作说明，不是项目运行依赖。仓库自身不启动浏览器、不保存登录态，也不实现 browser-assist session 状态机。

## 适用范围

当用户明确授权外部工具复用已经登录的 Chrome 时，可以使用当前客户端提供的 existing-Chrome 连接器做只读核对。连接器可能名为 wechat-chrome-session；其他等价实现也必须遵守同样边界。

普通 Playwright 隔离浏览器适合 localhost E2E，不应冒充用户已登录的公众号会话。

## 用户准备

1. 在公众号所在的 Chrome profile 打开 chrome://inspect/#remote-debugging 并开启远程调试。
2. 保持目标 mp.weixin.qq.com 标签页打开。
3. 关闭邮箱、银行、密码管理器等无关敏感标签页。
4. 由用户本人批准 Chrome 的调试连接提示。

用户不应向 Agent 提供 cookie、密码、二维码、AppSecret 或 token。

## 首次连接必须只读

外部工具按顺序：

1. 列出页面；
2. 只选择 host 为 mp.weixin.qq.com 的页面；
3. 获取 DOM snapshot；
4. 获取截图；
5. 输出脱敏连接报告后停止。

URL 必须去掉 query 和 fragment，不能输出 token。若有多个公众号页面，只列出脱敏标题和 path，由用户选择账号。若打开的是空白页、新 profile、登录页、验证码页或风控页，连接不合格，应立即停止。

建议报告：

    MCP/connector: wechat-chrome-session
    Connection: existing Chrome
    Target host: mp.weixin.qq.com
    Backend visible: yes/no
    Login required: yes/no
    DOM snapshot: yes/no
    Screenshot: yes/no
    Write actions: 0
    Result: PASS/BLOCKED

## 任务包核对

只有用户确认连接报告后，外部工具才可按照 export-agent-task 生成的 task.json 和 checklist.md：

- 定位指定草稿；
- 对比标题、摘要、封面、正文和合集；
- 截图或生成报告。

只读核对不得修改或保存草稿。任何时候都不得绕过扫码/验证码/风控，不得跨出任务包范围，不得删除内容，不得点击最终发布、群发或定时发布确认。平台出现安全提示时把控制权交还用户。

项目只接收用户提供的实际 proof；不会把连接报告或占位截图自动当作发布成功。
