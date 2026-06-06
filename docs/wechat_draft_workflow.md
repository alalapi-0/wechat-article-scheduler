# 微信公众号草稿流程

Status: Current draft-first workflow

## API Draft Mode

```text
本地文章
-> scan 入库
-> plan 生成 publish_jobs
-> run-once 到点执行
-> 渲染为公众号 HTML
-> 上传封面
-> API 创建微信公众号草稿
-> WECHAT_ENABLE_PUBLISH=false 时跳过正式发布
-> 本地记录草稿与事件
```

这是当前主链路。默认 `WECHAT_MODE=mock`，不联网；真实草稿测试必须显式设置 `WECHAT_MODE=real`，草稿-only 推荐同时设置 `WECHAT_ENABLE_PUBLISH=false`。

## External Agent Assist Mode

```text
本地文章
-> 渲染为公众号 HTML
-> API 创建草稿
-> 生成 external_agent_task_package
-> 用户交给 Hermes / Cursor Agent / Playwright MCP / Browser Use
-> 外部 Agent 辅助后台检查与设置
-> 外部 Agent 停在人机确认
-> 用户回填 proof
-> 本项目更新状态或记录 proof
```

External Agent Assist Mode 用于 API 无法覆盖的后台字段和视觉核对。当前项目只生成任务包，不在内部实现完整 Browser Agent，不保存浏览器登录态，不绕过验证码、扫码或风控，不默认点击最终发布。

## proof 示例

proof 可以是：

- 后台草稿截图路径。
- 外部 Agent 操作报告。
- 草稿确认结果描述。
- 用户明确确认后的发布链接。

没有 proof 的任务不能标记为已完成。

