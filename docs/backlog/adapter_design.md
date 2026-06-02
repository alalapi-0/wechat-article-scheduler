# 适配器设计

Status: Backlog / Not current development target

## 1. 适配器总原则

适配器封装平台交互，核心调度器只调用统一接口。新平台只新增 adapter、profile 和 payload 校验，不改核心状态机。

## 2. Adapter Registry

Adapter Registry 负责按 `platform + adapter_type` 查找适配器。

- 平台：`wechat_mp`、`zhihu`、`douban`、`bilibili`、`xiaohongshu` 等。
- 类型：`official_api`、`browser_assist`、`manual_export`、`local_blog`、`static_site`、`webhook`。
- Registry 不保存 secret，只持有 adapter 类和能力声明。

## 3. BaseAdapter 接口设计

```python
class BasePublishAdapter:
    adapter_type: str
    platform: str

    def validate_payload(self, payload) -> ValidationResult:
        ...

    def dry_run(self, payload) -> DryRunResult:
        ...

    def prepare(self, job) -> PrepareResult:
        ...

    def publish(self, job) -> PublishResult:
        ...

    def confirm(self, job, proof) -> ConfirmResult:
        ...
```

所有适配器都必须支持 `dry_run`，所有适配器都必须写 `publish_attempt`。

## 4. OfficialApiAdapter

- 可调用官方 API 创建草稿或发布。
- 必须支持 dry-run 与 payload 校验。
- 真实发布必须受 `safety_mode` 和显式开关控制。
- 微信公众号当前 real adapter 是该类型的历史实现。

## 5. BrowserAssistAdapter

- 只能 `prepare`，默认不直接最终发布。
- 生成操作说明、Playwright 步骤清单、截图路径和人工确认入口。
- 不绕过验证码、扫码、风控。
- 不保存 cookie。
- 必须进入 `waiting_confirmation` 并等待 proof。

## 6. ManualExportAdapter

- 生成 outbox 发布包。
- 可导出 Markdown、HTML、图片、视频、音频、平台说明。
- 不直接 publish。
- 人工发布后通过 proof 确认。

## 7. LocalBlogAdapter

- 输出到本地博客、静态站或文件目录。
- 可以把写文件视为发布成功，但仍需要 attempt 和事件。
- 必须避免覆盖未授权路径。

## 8. WebhookAdapter

- 用于通知飞书、Slack、企业微信等。
- Webhook 成功只代表通知成功，不代表第三方平台内容发布成功。
- 必须记录响应摘要并脱敏。

## 9. 平台能力矩阵

每个平台都要声明：内容类型、标题限制、正文限制、媒体限制、是否支持定时、是否需要 proof、登录/验证码风险、优先适配器类型。

## 10. 平台约束校验

约束校验在 `validate_payload` 和 `dry_run` 阶段完成。失败时不得进入 `scheduled`。

## 11. 适配器安全模式

`safety_mode`：

- `mock`：不联网。
- `draft_only`：仅创建草稿。
- `manual_only`：只导出或辅助，不最终发布。
- `real_publish`：允许真实发布，但必须有显式开关和审计。
