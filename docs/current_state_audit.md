# 当前状态审计

Status: Current P0 state audit

> 本文件已在路线收敛治理轮刷新。当前项目是个人本地微信公众号发布工作台，多平台内容只保留在 `docs/backlog/`。

## 2026-06 刷新摘要

- 当前已实现：CLI `init-db/scan/plan/run-once/scheduler`、FastAPI Web 工作台、网页批量上传作品与封面、SQLite 迁移、微信 mock/real adapter、真实微信草稿创建验证、事件审计与发布前预检。
- 当前第一保护对象：微信公众号草稿创建链路，尤其是 `scan -> plan -> run-once -> RealWechatAdapter.create_draft`。
- 当前安全默认：`WECHAT_MODE=mock` 不联网；显式设置 `WECHAT_MODE=real` 后进入真实 API 测试模式，默认允许验证草稿创建和正式发布接口；需要草稿-only 时设置 `WECHAT_ENABLE_PUBLISH=false`。
- 当前数据模型仍是微信单平台模型：`articles`、`publish_jobs`、`wechat_drafts`、`events`，外加 `collections`、`tags`、`article_tags`。
- 当前产品叙事：用户上传作品即视为想发布的内容，没有内容审核门禁；真实发布安全由默认 mock、real 模式显式切换、任务级发布选择、二次确认和预检承担。

## 审计范围

- 代码：`src/wechat_article_scheduler/` 全模块。
- 数据：`db.py` 基线 schema、`migrations/001..008` 与 SQLite 状态流转。
- 测试：`tests/` 中 CLI、调度、Web、微信 adapter、迁移、治理门控相关测试。
- 文档与治理：`README.md`、`docs/`、`governance/`、`project.yaml`、`scripts/agent_gate.py`。

## 已实现能力

- 本地 CLI 闭环：`init-db`、`scan`、`plan`、`run-once`、`scheduler`。
- 状态治理命令：`reject`、`retry-failed`、`events`、`content`。
- 本地 Web 工作台：上传、作品库、封面绑定、批量排期、预检、预览、回收站、到点自动执行。
- SQLite 表：`schema_migrations`、`articles`、`publish_jobs`、`wechat_drafts`、`events`、`collections`、`tags`、`article_tags`。
- Mock 适配器：不联网创建 mock media_id / publish_id。
- Real 适配器：真实 HTTP 能力（token、thumb、draft/add、freepublish/submit）+ 单测 mock。
- 真实 API 检查：`scripts/real_api_check.py` 可在人工配置 real 模式后创建真实草稿并写报告。

## 尚未完成

- 微信草稿更新能力。
- 更稳定的 Markdown 到微信公众号 HTML。
- 公众号效果预览快照。
- 封面裁剪与双比例预览。
- 多合集排期规则。
- scheduler 常驻运行文档和更完整失败恢复。
- API 不支持字段的微信公众号 browser_assist 流程。
- 完整微信公众号闭环验收。

## 保留但不作为当前实现的内容

- `src/wechat_article_scheduler/core/`
- `src/wechat_article_scheduler/content_packages/`
- `src/wechat_article_scheduler/platform_payloads/`
- `src/wechat_article_scheduler/manifests/`
- `src/wechat_article_scheduler/review/`
- `src/wechat_article_scheduler/adapters/manual_export/`
- `src/wechat_article_scheduler/adapters/local_blog/`
- `src/wechat_article_scheduler/adapters/webhook/`

这些目录是历史骨架或未来占位。阶段一不得继续扩展成多平台系统。

## 安全风险

- 若显式设置 `WECHAT_MODE=real`、`WECHAT_ENABLE_PUBLISH=true` 且任务级选择正式发布，可能触发真实发布。
- 不允许读取/打印 `.env`，不允许保存 cookie，日志不得输出 token。
- browser_assist 只能作为微信公众号本地自用后备方案；不得绕过验证码、扫码、风控，不得自动点击最终发布。
- 无官方 API 的未来平台默认只进入 backlog，不直接标记 `published`。

## 本轮治理结论

- `docs/roadmap_converged.md` 是当前执行路线入口。
- `docs/backlog/` 保存长期多平台材料，不是当前开发主线。
- 新功能必须优先服务微信公众号闭环。
- 下一轮优先执行“微信公众号现有链路稳定化”：错误码、摘要限制、草稿幂等、真实 API 报告和 CLI 回归。
