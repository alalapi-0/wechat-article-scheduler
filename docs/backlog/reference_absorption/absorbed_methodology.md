# 参考架构吸收方法论

Status: Backlog / Not current development target

本方法论把 TryPost、Mixpost、BrightBean Studio、Playwright MCP / browser_mcp 的可取模式转化为当前项目的长期工程原则。它是后续 40 轮推进的设计底座，不代表本轮已实现完整多平台发布。

## 1. Manifest 驱动原则

每个创作项目通过 `publish_manifest.json` 暴露待发布内容，发布器不侵入每个创作项目内部。

- 各项目只需要生成标准 manifest。
- 发布器统一负责导入、调度、适配、审计、确认。
- manifest 是项目边界，不要求创作项目迁移到本仓库目录。
- manifest 导入必须记录 hash，重复导入要幂等。
- manifest schema 必须版本化，新增字段保持向后兼容。

## 2. Content Package 原则

不再只把文章视为单个 Markdown 文件。每次发布应抽象为 `content_package`。

`content_package` 可以包含：

- 标题
- 正文
- 摘要
- 标签
- 封面
- 图片
- 视频
- 音频
- 平台专属字段
- 发布时间
- 目标平台
- 人工审核或确认要求

当前 `articles` 表是微信公众号文章链路的实现形态；未来 `content_package` 落地时必须兼容旧 `articles`，不能破坏 scan/plan/run-once。

## 3. Post + PlatformPost 双子模型原则

一个内容包可以发往多个平台。父内容包不直接承担所有平台状态。

- 每个平台必须有独立任务状态。
- 一个平台失败不应污染其他平台。
- 父内容包只聚合整体状态，如 `partially_published`。
- 平台子任务记录平台 ID、账号、错误、重试、发布证明。
- 微信公众号现有 `publish_jobs` 是单平台子任务的历史形态，未来迁移应小步兼容。

## 4. Platform Payload 原则

`canonical_text` 是主内容，`platform_payload` 是平台变体。

- 微信公众号、知乎、豆瓣、B站、小红书、抖音、快手等平台都需要自己的 payload。
- payload 应由规则生成，也允许人工改写。
- payload 必须记录 hash，便于判断是否需要重新 dry-run。
- payload 必须先 dry-run 校验，再进入 `scheduled`。
- 平台 payload 不应散落在 Web 表单、scheduler 或 adapter 内部。

## 5. Adapter Registry 原则

每个平台适配器必须注册，适配器不直接散落在业务逻辑中。

适配器类型至少包括：

- `official_api`
- `browser_assist`
- `manual_export`
- `local_blog`
- `static_site`
- `webhook`

新平台只新增 adapter 和平台 profile，不改核心状态机。当前 `WechatAdapter` 可保留为微信官方 API 适配器的历史实现，后续通过 registry 包装。

## 6. Dry-run First 原则

所有发布前必须先 dry-run。dry-run 不应联网执行最终发布。

Dry-run 检查：

- 字数限制
- 摘要长度
- 媒体格式
- 封面比例
- 平台必填字段
- 是否需要人工确认
- 是否有重复发布风险

Dry-run 输出 JSON 和 HTML 预览。JSON 供 Agent、测试和审计使用；HTML 供普通用户预览。

## 7. Publish Attempt 审计原则

每一次发布尝试都要记录，不只记录最终状态。

- 需要 `publish_attempt` 表。
- 同时可写 JSONL 镜像。
- 失败要记录错误码、错误摘要、响应片段、适配器类型、耗时。
- `events` 记录系统事件，`publish_attempt` 记录发布尝试，两者不能混淆。
- 真实平台响应片段必须脱敏，不能写 token、secret、cookie。

## 8. Review and Proof 原则

对无官方 API 或高风险平台，不能直接标记 `published`。

- 必须进入 `waiting_confirmation`。
- 人工发布后需要 `proof_of_publish`。
- proof 可以是平台链接、平台 post id、截图路径、手动备注。
- 无 proof 不应变成 `published`。
- browser_assist 和 manual_export 不得直接标记 `published`。
- official_api 返回平台 ID 后可直接 `published`，但仍要写 attempt 和事件。

本原则不恢复当前公众号内容审核门禁。它只服务未来多平台、半自动和高风险平台确认。

## 9. Idempotency and Dedup 原则

幂等用于防止重复发布。

- 防止 Agent 重试导致重复发布。
- 防止 scheduler 重启导致重复执行。
- 防止用户重复点击导致重复创建草稿。
- `content_fingerprint + platform_account_id` 应唯一。
- `idempotency_key` 应进入任务表或 attempt 表。
- 已知成功的幂等请求应返回历史结果，而不是重新发布。

## 10. Local First 原则

当前项目是个人工具，优先本地运行。

- 优先 SQLite。
- 优先本地文件。
- 优先 JSONL 审计镜像。
- 优先 Python 标准库和现有依赖。
- 以后可以部署 VPS，但不是第一阶段。
- 不引入多用户、计费、团队协作、商业 SaaS。

## 后续执行约束

- 大功能先写文档、接口、路线，再进入推进轮。
- 当前微信公众号草稿链路不得被多平台抽象破坏。
- 所有真实发布能力必须显式开关。
- 所有无官方 API 平台默认走 `manual_export` 或 `browser_assist`。
- browser_assist 必须有人在环，不绕过验证码、扫码、风控。
