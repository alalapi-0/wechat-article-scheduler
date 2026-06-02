# 迁移计划：微信公众号阶段一

Status: Current P0 migration plan

## 目标

在不破坏现有 CLI 与微信公众号草稿链路的前提下，逐步稳定个人本地微信公众号发布工作台。

当前迁移目标不是多平台工作台。`content_package`、`platform_payload`、`publish_attempt`、`publish_manifest`、多平台 adapter 等长期设计已进入 `docs/backlog/`。

## 迁移原则

- 小步、可回滚、可测试。
- 先文档，再骨架，再实现。
- 保持 `scan/plan/run-once` 命令稳定。
- 默认 `WECHAT_MODE=mock`。
- `WECHAT_MODE=real` 是显式真实 API 测试模式，默认允许验证草稿创建和正式发布接口。
- 需要草稿-only 时，显式设置 `WECHAT_ENABLE_PUBLISH=false`。
- 真实发布必须由任务级正式发布选择触发。
- 不为了未来平台迁移当前微信数据表。

## 阶段 A：现有微信链路稳定化

- 统一摘要 120 字限制。
- 微信错误码分类。
- 草稿创建幂等。
- real draft-only 回归测试。
- 保留 mock 默认不联网，并明确 real API 测试模式。

## 阶段 B：微信公众号渲染与预览

- Markdown 到微信公众号 HTML。
- 公众号正文预览。
- 发布前内容质量检查。
- HTML 转义和重复标题处理。

## 阶段 C：封面与合集

- 单篇封面和默认封面。
- 封面裁剪配置。
- 方形/横向封面预览。
- 多合集 `collection.yaml`。
- 合集排期规则。

## 阶段 D：本地 scheduler 与 Web 控制台

- 队列状态稳定化。
- 失败重试和事件日志。
- scheduler 常驻运行文档。
- 文章详情、草稿、队列、设置和事件日志页面。

## 阶段 E：草稿更新、人工确认与 browser_assist

- 微信草稿更新能力核验。
- 微信字段能力矩阵核验。
- API 不支持字段进入人工确认或 browser_assist。
- browser_assist 只做本地自用后备方案，不绕过验证码，不保存密码/cookie，不默认最终发布。

## 风险与缓解

- 风险：迁移破坏已跑通微信链路。缓解：每轮保留 CLI 和 adapter 回归测试。
- 风险：误触正式发布。缓解：默认仍是 `WECHAT_MODE=mock`；real 模式必须显式设置；任务级“仅草稿”不会触发正式发布。
- 风险：browser_assist 越界。缓解：仅辅助打开后台、填表、截图和等待人工确认。
- 风险：backlog 设计误导当前开发。缓解：长期文档统一放入 `docs/backlog/`。
