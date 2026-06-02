# 自动发布参考架构综合吸收

Status: Backlog / Not current development target

## 本轮参考报告摘要

本轮参考 TryPost、Mixpost、BrightBean Studio、Playwright MCP / browser_mcp 的架构逻辑，但不复制源码、不 fork 整仓、不引入重型技术栈。本项目的当前第一目标仍是保护微信公众号草稿创建链路，并在文档、协议、目录骨架和长期路线图层面吸收可复用的工程模式。

长期定位升级为：本地多内容、多项目、多平台定时发布工作台。这个升级是长期目标，不代表本轮已经支持知乎、豆瓣、小红书、视频号、抖音、快手、Bilibili 或网易云音乐发布。

## TryPost 可吸收点

- `Post + PostPlatform` 双子模型：父内容聚合整体生命周期，平台子任务独立记录状态、错误和发布证明。
- 状态机：`draft -> scheduled -> publishing -> published / partially_published / failed` 可转化为本项目的长期发布状态。
- 到期任务原子 claim：本地 SQLite 也需要 claim token 与状态条件更新，避免重复执行。
- 每个平台一个 Publisher：可转化为 Adapter Registry。
- 发布前校验：平台字段、媒体规则、meta 必须先 dry-run。
- MCP / REST API：未来可为 Agent 暴露受控 `list_jobs/dry_run/approve/attach_proof`，但不暴露无鉴权真实 publish。

## Mixpost 可吸收点

- `PostVersion`：每个平台或账号可以有文案变体，不把所有平台都绑死在同一正文。
- `PostAccount`：同一平台多账号需要独立账号配置、安全模式和能力约束。
- `SocialProviderPostConfigs`：平台 payload 与平台限制配置化，避免规则散落在业务逻辑。
- 状态与调度状态分离：发布结果状态不等于队列调度状态。

## BrightBean 可吸收点

- `Post + PlatformPost + PublishLog`：非常适合转化为 `content_package + platform_payload/publish_job + publish_attempt`。
- 每个平台独立状态、错误、重试次数、`next_retry_at`。
- 审批流和人工确认：本项目不恢复公众号内容审核，但需要为高风险平台设计 `review_required` 与 `waiting_confirmation`。
- `PublishLog / attempt`：每一次尝试都应落库，失败排障不能只看最终状态。
- `IdempotencyRecord`：防止 Agent 重试、scheduler 重启、用户重复点击导致双发。
- 轻量审计：用 SQLite + JSONL 镜像即可，不引入全栈后台。

## Playwright MCP / browser_mcp 可吸收点

- 浏览器是辅助工具，不是绕过平台风控的发布机器人。
- 对无开放 API 的中文平台，适配器类型应是 `browser_assist`。
- browser_assist 只做打开后台、辅助填表、截图、等待人工确认。
- 不绕过验证码、扫码、登录风控，不保存后台 cookie，不自动点击最终发布按钮。
- browser_assist 必须与 `waiting_confirmation`、`proof_of_publish` 绑定。

## 不建议吸收的内容

- 不 fork TryPost。
- 不嵌入 Mixpost。
- 不照搬 BrightBean。
- 不做全栈 SaaS。
- 不引入 Laravel、Django、Redis、PostgreSQL 或大型前端 monorepo。
- 不做多用户、计费、团队协作、商业后台。
- 不把浏览器自动化当成无人工确认的最终发布能力。

## 当前项目应该吸收的模式

- `Post + PlatformPost` 思想，落地为 `content_package + platform_payload + publish_job`。
- `PostVersion` 思想，落地为 `canonical_text + platform_payload`。
- `PublishLog` 思想，落地为 `publish_attempt` 与 JSONL 镜像。
- `IdempotencyRecord` 思想，落地为 `idempotency_key/content_fingerprint`。
- `Approval` 思想，限定为多平台半自动任务的 `review_required/waiting_confirmation/proof`。
- `browser_assist` 思想，限定为有人在环的辅助适配器。

## 当前项目不应该吸收的模式

- 不把当前个人工具改造成 SaaS。
- 不把 SQLite 立即替换成 PostgreSQL。
- 不引入 Redis 队列。
- 不把现有微信 adapter 改成参考仓源码结构。
- 不把所有平台都假设为有官方 API。
- 不把 proof 缺失的 browser/manual 任务直接标记为 `published`。

## 当前项目与参考仓库的差异

- 当前项目是本地个人工具，参考仓库多为 SaaS 或全栈系统。
- 当前项目已真实跑通微信公众号草稿创建，参考吸收不能破坏该链路。
- 当前项目默认 mock 与 draft-only，参考仓库通常更接近正式发布平台。
- 中文封闭平台风控更强，不能照搬国外社媒 API 发布假设。
- 当前项目以 Python + SQLite + 本地文件为主，重依赖必须推迟。

## 轻量化改造方向

- 先写文档和接口骨架，再逐轮迁移。
- 先支持 manifest 导入、content_package、platform_payload、publish_attempt，再做新平台。
- 新平台先 `manual_export`，再 `browser_assist`，最后才研究 `official_api`。
- 每个真实发布能力都必须有显式开关、dry-run、审计和 proof。
