# 已登录 Chrome 只读连接

这是可选的外部浏览器协作说明，不是项目运行依赖。仓库自身不启动浏览器、不保存登录态，也不实现 browser-assist session 状态机。

## 适用范围

当用户明确授权外部工具复用已经登录的 Chrome 时，可以使用当前客户端提供的 existing-Chrome 连接器做只读核对。连接器可能名为 wechat-chrome-session；其他等价实现也必须遵守同样边界。

记录实际客户端、连接方式和固定版本后再验收；`@latest` 不是固定版本，版本未知时停止核对。本文不安装连接器，也不表示当前客户端、真实账号或页面已通过演练。

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
2. 将 host 为 mp.weixin.qq.com 的页面列为候选，显式选择并绑定页面句柄（如 pageId 或 tabId）；
3. 核对句柄仍指向所选页面，检查可见账号身份；确认与用户指定账号匹配后，获取 DOM snapshot；
4. 再次复核同一页面句柄、页面身份和可见账号后，获取截图；
5. 输出脱敏连接报告后停止。

URL 必须去掉 query 和 fragment，不能输出 token。若有多个候选页面或账号，只列出脱敏标题和 path，停止并交由用户指定页面与账号；不能自行选择第一页或当前页。host、标题或客户端的“已选中”状态，均不能单独证明账号和任务归属。账号可见身份不明、空白页、新 profile、登录页、验证码页或风控页均不合格，应立即停止。

每次快照、截图和后续任务核对前，都重新确认绑定的页面句柄、页面身份、可见账号及适用的任务草稿匹配。页面关闭、替换、导航后身份不明、句柄失效或工具回退到其他页时，立即停止并交还用户；即使回退页也在同一 host，也不能据此继续。不得接管无关标签页来补足核对。

建议报告：

    MCP/connector: wechat-chrome-session
    Client/version: 实际客户端和固定版本 / unknown
    Connection: existing Chrome
    Target host: mp.weixin.qq.com
    Page identity: confirmed/unknown
    Account match: confirmed/unknown
    Task/draft match: confirmed/unknown/not applicable (connection only)
    Backend visible: yes/no
    Login required: yes/no
    DOM snapshot: yes/no
    Screenshot: yes/no
    Write actions: 0
    Result: PASS/BLOCKED
    Stop reason: none/具体原因

报告只记录上述脱敏身份结论、版本、核对结果和停止原因，不写 cookie、token、完整带参数 URL 或会话文件。连接报告的 PASS 只表示本次只读连接检查通过，不表示任务草稿已核对或发布成功。

## 任务包核对

只有用户确认连接报告后，外部工具才可按照 export-agent-task 生成的 task.json 和 checklist.md：

- 根据 task.json/checklist.md 定位指定草稿，并在绑定页面上核对可见账号、目标草稿和任务身份；只匹配标题不足以确认目标；
- 对比标题、摘要、封面、正文和合集；
- 截图或生成报告。

只读核对不得修改或保存草稿。任何时候都不得绕过扫码/验证码/风控，不得跨出任务包范围，不得删除内容，不得点击最终发布、群发或定时发布确认。平台出现安全提示时把控制权交还用户。

多账号、多个候选草稿或任务归属不明时停止，不通过自动切换页面、标题猜测或保存草稿来消除不确定性。页面和账号已确认，但任务草稿尚未确认时，报告必须保留 unknown，不能开始内容一致性结论。

项目只接收用户提供的实际 proof；不会把连接报告或占位截图自动当作发布成功。
