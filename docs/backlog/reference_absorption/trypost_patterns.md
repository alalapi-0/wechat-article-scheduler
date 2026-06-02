# TryPost 模式吸收

## 可吸收模式

- `Post + PostPlatform`：父内容与平台任务分离。
- 平台 Publisher：平台差异集中在适配器，不散落在 scheduler 或 Web。
- 原子 claim：到期任务执行前用状态条件和 claim token 抢占。
- 平台校验：发布前校验字段、媒体、账号、meta。
- API 面向 Agent：未来可提供受控的 dry-run 和任务查询接口。

## 本项目落点

- 父层：`content_package`。
- 子层：`platform_payload` 和 `publish_job`。
- 状态：父层聚合，子任务独立失败。
- 调度：SQLite 条件更新模拟原子 claim。
- 适配器：Adapter Registry 注册 `official_api/browser_assist/manual_export/local_blog/webhook`。

## 不吸收

- 不 fork TryPost。
- 不引入 Laravel。
- 不做 SaaS 租户、计费、团队权限。
- 不把当前微信链路迁移到 TryPost 代码结构。
