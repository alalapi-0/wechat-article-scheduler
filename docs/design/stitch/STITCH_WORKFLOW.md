# Stitch 设计工作流

## 1. 定义任务

从 `UI_TASKS.md` 复制最接近的模板，补齐页面目标、用户、输入数据、核心动作、风险动作、状态和验收标准。先确认任务属于当前微信公众号 P0，不把后期多平台 backlog 偷渡进主界面。

## 2. 形成 Prompt

使用 `PROMPT_TEMPLATES.md`，明确：

- 个人用户、中文界面、桌面优先；
- 普通/详情/高级信息分层；
- mock、dry-run、real_api、draft-only 的安全提示；
- 当前技术栈和禁止生成营销落地页；
- loading、empty、success、error、disabled 状态。

将实际 prompt 保存到 `prompts/`。

## 3. 生成与导出

用 Stitch 创建项目或 screen，必要时生成 2-3 个 variants。获取 screen HTML 与 screenshot，并按 `EXPORT_GUIDE.md` 保存。不要把下载 URL、临时 token 或 key写入仓库。

## 4. 评审

在 `reviews/` 记录：

- 采用的布局、组件和文案；
- 与现有产品原则冲突的部分；
- 需要保留的业务逻辑与安全门控；
- 无法直接落地的框架或依赖；
- 拆分后的实现任务和浏览器验收路径。

## 5. 实现

按现有 Web 模块和原生 HTML/CSS/JS 模式实现。Stitch HTML 只用于理解结构和视觉，不直接覆盖业务代码，不绕过 service、API、数据库或真实发布确认。

## 6. 验证

启动本地服务后，用 Playwright 或 chrome-devtools：

1. 打开真实页面。
2. 走至少一条核心用户路径。
3. 检查 empty/loading/success/error。
4. 检查 console 无未处理 error。
5. 检查核心 network 请求无意外 4xx/5xx。
6. 验证 `1280x900`，并兼容 `768` 与 `375` 宽度。
7. 运行对应 pytest 和 `python3 scripts/agent_gate.py gate`。
