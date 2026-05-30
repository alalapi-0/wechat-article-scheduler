# 当前状态审计（Round 1 治理轮）

## 审计范围

- 代码：`src/wechat_article_scheduler/` 全模块（CLI、扫描、解析、排期、调度、适配器、Web）
- 数据：`db.py` 中 SQLite schema 与状态流转
- 测试：`tests/` 全量现有测试 + 本轮新增最小测试
- 文档与治理：`README.md`、`docs/`、`governance/`、`project.yaml`

## 已实现能力

- 本地 CLI 闭环：`init-db`、`scan`、`plan`、`run-once`、`scheduler`
- 状态治理命令：`reject`、`retry-failed`、`events`
- 本地 Web 管理页（FastAPI + 简单 HTML）
- SQLite 四表：`articles`、`publish_jobs`、`wechat_drafts`、`events`
- Mock 适配器：不联网创建 mock media_id / publish_id
- Real 适配器：真实 HTTP 能力（token、thumb、draft/add、freepublish/submit）+ 单测 mock

## 真实可用能力（可直接用于生产前人工流程）

- 本地扫描与去重入库（`articles/inbox -> imported`）
- 可追溯排期（`publish_jobs` + `events`）
- 人工触发执行 `run-once` 与 dry-run 报告
- `WECHAT_MODE=real` 时可调用真实 API（前提：凭证和网络白名单准备好）

## Mock / 半成品能力

- Web 控制台仍为轻量内嵌页面，不是完整运营后台
- 调度器是单进程轮询，缺少多实例协调与抢占
- 渲染能力仅提供最小 Markdown 段落骨架，未覆盖复杂富文本
- 封面资产管理、内容库、迁移系统目前仅有目录骨架与设计文档

## 已知问题

- 历史默认摘要长度为 200，可能超出微信 `digest` 常见 120 字约束（本轮已修复为 120）
- 文档中“real 适配器骨架”描述落后于代码现状（实际已有 HTTP 调用实现）
- `scheduler.py` 与 `scheduler/` 包并存，需要兼容层维持导入稳定（本轮已加）

## 技术债

- 调度与发布流程尚未拆分领域层（目前集中在 `scheduler.py`）
- Web API 仍无鉴权和细粒度权限模型
- 数据迁移体系缺少版本化 SQL 迁移脚本

## 安全风险

- 若误将 `WECHAT_MODE=real` 且 `WECHAT_ENABLE_PUBLISH=true` 放在无人值守环境，可能触发真实发布
- 目前无“强制人工审核闸门”字段，主要依赖配置与操作规范
- 本地日志虽已脱敏 token/secret，但仍需控制日志文件权限和保留策略

## 数据结构风险

- `publish_jobs` 以字符串时间和状态驱动，未建立更严格状态机约束
- `events.payload_json` 为自由文本，后续统计分析需要更稳定 schema
- `articles.summary` 历史数据可能存在超 120 的旧记录（运行时会截断并记录 warning 事件）

## 文档不一致

- 旧版 README 与 rounds 文档对产品定位偏“调度器”，缺少“本地发布工作台”定位
- 架构文档未及时反映 Round 5~7 的真实实现边界

## 小修复建议（本轮执行）

- 统一摘要上限到 120（解析、扫描默认值、真实上传前兜底）
- 草稿上传前自动截断并写 `digest_truncated_warning` 审计事件
- 增加渲染器骨架与 Markdown 段落渲染测试
- 增加 digest 截断行为测试

## 后续建议

- Round 2：补“人工审核闸门”与审批状态字段（默认不自动发布）
- Round 3：将调度器拆分为 `scheduler/domain` 与 `scheduler/runtime`
- Round 4：完善内容库与封面资产的可追溯元数据
- Round 5：补齐 Web 控制台鉴权、审计过滤与只读视图
