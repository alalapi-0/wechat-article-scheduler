# 路线收敛审计

Status: Current P0 governance document

## 1. 当前已经实现

当前仓库已经具备一个可运行的微信公众号本地发布基础链路：

- CLI 入口：`src/wechat_article_scheduler/cli.py`，命令包括 `init-db`、`scan`、`plan`、`run-once`、`scheduler`、`serve`、`events`、`reject`、`retry-failed`。
- 微信 API 代码：`src/wechat_article_scheduler/adapters/real.py` 负责 token、封面素材上传、`draft/add`、`freepublish/submit`；`src/wechat_article_scheduler/adapters/wechat_http.py` 负责 HTTP、token 缓存和脱敏。
- Mock 适配器：`src/wechat_article_scheduler/adapters/mock.py`，用于默认演练。
- 调度链路：`src/wechat_article_scheduler/plan.py`、`src/wechat_article_scheduler/scheduler/runtime.py`、`src/wechat_article_scheduler/scheduler/domain.py`。
- 渲染链路：`src/wechat_article_scheduler/renderers/wechat.py`、`src/wechat_article_scheduler/publish_preview.py`、`src/wechat_article_scheduler/publish_body.py`。
- Web 工作台：`src/wechat_article_scheduler/web/app.py` 与 `admin_template.html`，提供上传、列表、排期、预览、队列、状态和预检。
- SQLite 表：`schema_migrations`、`articles`、`publish_jobs`、`wechat_drafts`、`events`、`collections`、`tags`、`article_tags`。
- 内容样稿：`articles/imported/` 已纳入仓库，供 scan/plan 测试使用。
- 已验证能力：真实微信公众号 API 已成功创建草稿；`WECHAT_ENABLE_PUBLISH=false` 时应只创建草稿；摘要 digest 已按 120 字限制做兜底截断。

## 2. 当前真正卡点

当前项目的卡点不是“缺少多平台”，而是微信公众号闭环还没有足够稳定：

- 摘要、错误码、幂等和失败重试需要继续稳定。
- Markdown 到微信公众号 HTML 的排版需要更可控。
- 公众号效果预览仍需和实际草稿渲染更接近。
- 封面上传、方形/横向裁剪预览、默认封面策略还不完整。
- Web 控制台需要围绕文章详情、预览、草稿、队列、事件日志做 MVP 收口。
- 本地 scheduler 需要常驻运行方式、重试状态和失败恢复说明。
- 草稿更新能力还没有成为稳定能力。
- 微信官方 API 不覆盖的字段需要人工确认或 browser_assist 后备流程。

## 3. 路线为什么开始发散

Round 56 前，项目吸收了 TryPost、Mixpost、BrightBean、Playwright MCP 等参考仓库的模式。这些模式有长期价值，但被过早放进当前路线后，项目叙事开始从“我自己用的微信公众号发布工作台”滑向“多平台发布器”。

发散信号包括：

- Round 56 前，`project.yaml`、`docs/product_vision.md`、`docs/architecture.md` 出现“多内容、多项目、多平台定时发布工作台”的当前定位；本轮已改为微信公众号优先。
- Round 56 前，`docs/roadmap_40_rounds.md` 把知乎、豆瓣、小红书、Bilibili、抖音、快手、网易云音乐等平台排进后续开发轮；本轮已移动到 `docs/backlog/roadmap_40_rounds.md`。
- Round 56 前，`docs/adapter_design.md`、`docs/platform_capability_matrix.md`、`docs/multi_project_manifest_design.md`、`docs/data_model_design.md` 过早强调 adapter registry、platform_payload、publish_manifest、多项目、多媒体统一模型；本轮已移动到 `docs/backlog/`。
- `src/wechat_article_scheduler/core/`、`content_packages/`、`platform_payloads/`、`manifests/`、`review/` 等轻量骨架存在，但当前微信 CLI 并未通过这些模块运行。

## 4. 长期有价值的参考设计

以下设计保留为 backlog 方法，不进入阶段一开发主线：

- `Post + PlatformPost` 或 `content_package + platform_payload`：未来多平台时用于分离主内容和平台变体。
- `publish_attempt`：未来用于区分系统事件和具体发布尝试。
- `proof_of_publish`：未来用于 manual_export 和 browser_assist 的人工确认。
- `adapter registry`：未来平台数量真正增加后再引入。
- `manual_export`：未来文本平台或无 API 平台的低风险起点。
- `browser_assist`：仅在微信公众号 API 不覆盖字段时作为本地自用后备方案。
- `publish_manifest`：未来跨项目导入再考虑，当前不作为微信公众号 MVP 的输入协议。

## 5. 当前阶段不该实现的设计

阶段一不实现以下内容：

- 知乎、豆瓣、小红书、抖音、快手、Bilibili、网易云音乐等平台适配。
- 完整多平台 adapter registry。
- 视频、音频、音乐统一发布。
- 完整 `publish_manifest` 多项目系统。
- 多租户、团队、计费、商业 SaaS。
- 大型前端框架、Redis、PostgreSQL、分布式队列。
- 无人值守 browser_assist 最终发布。

## 6. 降级为 backlog 的文档

本轮将以下文档移动或标记到 `docs/backlog/`：

- `docs/backlog/roadmap_40_rounds.md`
- `docs/backlog/data_model_design.md`
- `docs/backlog/adapter_design.md`
- `docs/backlog/platform_capability_matrix.md`
- `docs/backlog/content_package_design.md`
- `docs/backlog/multi_project_manifest_design.md`
- `docs/backlog/review_and_proof_design.md`
- `docs/backlog/reference_absorption/`

这些文档只作为长期参考，不作为当前开发任务来源。

## 7. 保留但不开发的模块

以下目录可保留为历史骨架或未来占位，但阶段一不得继续扩展：

- `src/wechat_article_scheduler/core/`
- `src/wechat_article_scheduler/content_packages/`
- `src/wechat_article_scheduler/platform_payloads/`
- `src/wechat_article_scheduler/manifests/`
- `src/wechat_article_scheduler/review/`
- `src/wechat_article_scheduler/adapters/manual_export/`
- `src/wechat_article_scheduler/adapters/local_blog/`
- `src/wechat_article_scheduler/adapters/webhook/`

当前运行主线仍是 `scan -> plan -> run-once -> WeChat adapter`。

## 8. 应删除、合并或归档的内容

不删除重要文档；本轮采用归档和降级：

- 长期多平台路线进入 `docs/backlog/`。
- 当前产品愿景重写为阶段一微信公众号优先。
- 架构文档重写为微信公众号优先架构。
- README 明确“当前不是多平台发布器”。
- `repo_protocol_standard.yaml` 增加阶段一禁止事项和 browser_assist 边界。

## 9. 当前最应该推进的微信公众号闭环

阶段一最应该推进的闭环是：

本地文章导入 -> 去重 -> 多合集管理 -> 微信 HTML 渲染 -> 摘要 120 字处理 -> 封面管理和双比例预览 -> 创建/更新微信草稿 -> Web 预览 -> 本地排期 -> scheduler 到点执行 -> 失败重试 -> 事件日志 -> 人工确认 -> 可选正式发布。

如果官方 API 无法覆盖某些后台字段，则进入：

API 创建草稿 -> Web 控制台预览 -> browser_assist 打开公众号后台 -> 辅助定位草稿或填写字段 -> 用户人工确认 -> 用户保存或发布 -> 回填 proof -> 本地状态更新。

## 10. 下一轮建议

下一轮应进入：Round 2：微信公众号现有链路稳定化。

优先任务：

- 统一摘要 120 字限制的入口和测试。
- 梳理微信错误码到本地可读错误。
- 增强草稿创建幂等，避免重复创建。
- 保证 `WECHAT_ENABLE_PUBLISH=false` 时永远不触发正式发布。
- 增加 real draft-only 的回归测试和 smoke 说明。
