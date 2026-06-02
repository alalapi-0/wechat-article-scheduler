# 开发路线图（Round 0 ~ Round 59）

本文件是路线图**人类权威源**；机器可读状态见 `governance/round_state.yaml`，机器轮次注册表见 `scripts/agent_gate.py` 的 `ROUND_ORDER` / `ROUND_META`。
任何轮次调整都必须同次同步 `tests/test_agent_gate.py` 与治理范围字段。

> **产品定位（Round 56 路线收敛后的权威表述）**：本项目是个人本地微信公众号发布工作台，P0 只服务微信公众号闭环。知乎、豆瓣、小红书、视频号、Bilibili、抖音、快手、网易云音乐等平台全部进入后期 backlog，不抢占阶段一资源。真实 API 测试策略 = 默认 `WECHAT_MODE=mock` 不联网；显式切到 `WECHAT_MODE=real` 后用于真实草稿和真实发布接口测试；需要草稿-only 时设置 `WECHAT_ENABLE_PUBLISH=false`；执行到点前仍有二次确认 + 发布前预检清单。历史轮次（Round 0–42）中出现的"审核/review_status"叙事已在 Round 43 移除；参考仓吸收成果只保留可帮助微信公众号闭环的设计，其余按 `docs/backlog/` 管理。

> 当前执行路线入口：`docs/roadmap_converged.md`。历史 Round 0–56 仍保留在本文件供 gate 校验和追溯，长期多平台蓝图已降级为 backlog。

## 推进总流程（强制）

1. 文档先行：先更新本文件的目标、范围、验收与交付清单
2. 再实现：按轮次边界修改代码/测试/文档
3. 再 gate：执行 `python scripts/agent_gate.py gate` 与相关测试
4. 再 advance：仅在明确授权时执行 `python scripts/agent_gate.py advance --commit`

## 产出物命名规范

- 轮次完成报告：`docs/reports/round_XXX_completion.md`
- 轮次风险补充：`docs/reports/round_XXX_risk_notes.md`（可选）
- 门控报告：`docs/reports/agent_gate_report.md`
- 报告模板：`docs/reports/round_report_template.md`

## Phase 总览

| Phase | 范围 | 定位 |
|---|---|---|
| Phase 0 治理地基 | Round 0 ~ Round 2 | 建立 CLI 闭环、治理规范、内容建模 |
| Phase 1 产品化 MVP | Round 3 ~ Round 6 | 架构分层、迁移能力、Web 初版与渲染扩展 |
| Phase 2 发布可靠性 | Round 7 ~ Round 9 | 资产管理、可观测、产品化收口 |
| Phase 3 可用性与治理细化 | Round 10 ~ Round 12 | 工作台基础体验、路线图执行化、质量门禁 |
| Phase 4 内容生产能力 | Round 13 ~ Round 15 | Renderer、Cover、Content Library、多合集细化 |
| Phase 5 发布编排与真实能力 | Round 16 ~ Round 18 | Scheduler、真实发布、能力矩阵与 AI 辅助 |
| Phase 6 普通用户视图与主流程 | Round 19 ~ Round 25 | 普通视图原则、术语人话化、信息减法、三步操作、反馈、空状态、真实发布护栏 |
| Phase 7 桌面工作台信息架构 | Round 26 ~ Round 30 | 桌面主布局、文章列表、发布队列、事件时间线、高级信息开关 |
| Phase 8 体验固化与后续接入规范 | Round 31 ~ Round 38 | 帮助解释、错误恢复、桌面效率、窄屏兼容、E2E 基线、非技术用户走查、MVP 收口、后续功能接入规范 |
| Phase 9 维护与生产加固 | Round 39 ~ Round 42 | Web 发布前确认入口、定时发布 UX、真实发布预检、能力矩阵维护 |
| Phase 10 产品重定位：批量发布工作台 | Round 43 ~ Round 46 | 移除审核概念、网页批量上传作品与封面、工作台界面与配色重构、发布确认护栏收口 |
| Phase 11 内容发布正确性与管理能力 | Round 47 ~ Round 53 | UI 细节修正、标题去重、公众号效果预览、回收站与彻底删除、批量管理、发布前内容质量检查 |
| Phase 12 真实 API 与路线收敛 | Round 54 ~ Round 56 | 真实微信 API 验证、auto-approved pipeline、路线收敛治理 |

## Round 状态快照

| Round | 主题 | 状态 |
|---|---|---|
| Round 0 | CLI MVP 闭环 | 已完成 |
| Round 1 | 治理轮 | 已完成 |
| Round 2 | 内容库建模 | 已完成 |
| Round 3 | 调度域模块化 | 已完成 |
| Round 4 | 数据迁移体系 | 已完成 |
| Round 5 | Web 控制台增强 | 已完成 |
| Round 6 | 渲染与模板扩展 | 已完成 |
| Round 7 | 封面资产管理 | 已完成 |
| Round 8 | 可观测与运维 | 已完成 |
| Round 9 | 发布工作台产品化 | 已完成 |
| Round 10 | 基础工作台可用性升级 | 已完成 |
| Round 11 | 路线图执行化与治理编排 | 已完成 |
| Round 12 | 持续演进与质量门禁强化 | 已完成 |
| Round 13 | Renderer 内容渲染深化 | 已完成 |
| Round 14 | Cover 封面资产工作流 | 已完成 |
| Round 15 | Content Library 与多合集 | 已完成 |
| Round 16 | Scheduler 编排与人工闸门 | 已完成 |
| Round 17 | 真实发布安全试运行 | 已完成 |
| Round 18 | 能力矩阵与 AI 辅助入口 | 已完成 |
| Round 19 | 普通用户工作台原则与 Playwright 视觉基线 | 已完成 |
| Round 20 | 术语人话化与中文文案标准 | 已完成 |
| Round 21 | 普通视图信息减法 | 已完成 |
| Round 22 | 三步操作主流程 | 已完成 |
| Round 23 | 人话反馈系统 | 已完成 |
| Round 24 | 空状态与首次使用 | 已完成 |
| Round 25 | 安全发布护栏 | 已完成 |
| Round 26 | 桌面主布局 | 已完成 |
| Round 27 | 文章列表普通化 | 已完成 |
| Round 28 | 发布队列普通化 | 已完成 |
| Round 29 | 事件日志时间线 | 已完成 |
| Round 30 | 高级信息开关 | 已完成 |
| Round 31 | 帮助与解释系统 | 已完成 |
| Round 32 | 错误与恢复指引 | 已完成 |
| Round 33 | 桌面效率优化 | 已完成 |
| Round 34 | 窄屏兼容验收 | 已完成 |
| Round 35 | Playwright E2E 可用性基线 | 已完成 |
| Round 36 | 非技术用户走查报告 | 已完成 |
| Round 37 | Web 控制台 MVP 收口 | 已完成 |
| Round 38 | 后续功能接入规范 | 已完成 |
| Round 39 | Web 发布前确认入口 | 已完成 |
| Round 40 | 定时发布 UX | 已完成 |
| Round 41 | 真实发布预检清单 | 已完成 |
| Round 42 | 能力矩阵维护 | 已完成 |
| Round 43 | 产品重定位与审核概念移除 | 已完成 |
| Round 44 | 网页批量上传作品与封面 | 已完成 |
| Round 45 | 工作台界面与配色重构 | 已完成 |
| Round 46 | 发布确认护栏与能力矩阵收口 | 已完成 |
| Round 47 | 轻量 UI 细节修正 | 已完成 |
| Round 48 | 微信草稿正文规范化与标题去重 | 已完成 |
| Round 49 | 公众号效果预览修正 | 已完成 |
| Round 50 | 作品回收站与可逆删除 | 已完成 |
| Round 51 | 清空回收站与彻底删除 | 已完成 |
| Round 52 | 批量管理与删除一致性 | 已完成 |
| Round 53 | 发布前内容质量检查 | 已完成 |
| Round 54 | 真实微信 API 闭环验证 | 已完成 |
| Round 55 | Auto-Approved Real API Pipeline | 已完成 |
| Round 56 | 路线收敛治理轮 | 已完成 |
| Round 57 | 收敛后微信链路稳定化 | 已完成 |
| Round 58 | 摘要错误码与草稿幂等 | 已完成 |
| Round 59 | 微信公众号 HTML 渲染器 | 已完成 |

## 轮次字段规范

每一轮必须维护以下字段：目标、范围、非目标、输入、输出、验收标准、建议测试/冒烟命令、退出标准、风险、回滚点、交付项。
未来 Agent 不得只用一句话标记完成；缺少验收命令或退出标准时，视为路线图 drift，需要同步 `docs/rounds.md`、`scripts/agent_gate.py` 与 `tests/test_agent_gate.py`。

## 当前实现边界

- 当前已实现：CLI scan/plan/run-once、mock/real adapter 基础能力、SQLite 审计、桌面优先 Web 工作台、**网页批量上传作品与封面**、每篇作品独立封面、发布前确认与预检、真实微信草稿验证、治理 gate。
- 已移除：**"审核 / review_status" 概念**（Round 43 起）。用户上传的作品即视为想发布的内容，不再有审核步骤；真实发布安全改为「默认演练 + 显式开关 + 二次确认 + 预检清单」。
- 可用性成果（贯穿主题，Phase 6 / Phase 7 / Phase 8，Round 19–38）：把后台从“工程师能用”改造成“完全不懂编程的人也一看就懂”的桌面浏览器本地工作台。默认普通视图只回答“现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办”；技术元数据、原始 JSON、数据库路径、内部状态字段默认进入“高级信息”开关或调试页。产品原则是 **Desktop-first local workbench**：优先保证电脑浏览器里的信息密度、批量处理效率、表格可读性、左侧导航/顶部状态与主内容区组织；**Responsive compatibility** 只作为兼容验收，确保窄屏不横向溢出、关键按钮可点、页面可读，但不把手机看板作为默认布局目标。
- 暂不做：React/Vue 控制台、商业化多用户后台、网页登录公众号后台、cookie 保存、默认真实发布、无人工确认的 browser_assist 最终发布。未来多平台 review/proof 仅用于 browser_assist/manual_export 的人工确认，不恢复当前公众号内容审核门禁。

---

## Phase 0：治理地基

### Round 0 - CLI MVP 闭环

- 目标：形成最小可运行闭环，验证扫描-排期-执行路径。
- 范围：`init-db`、`scan`、`plan`、`run-once`。
- 非目标：Web UI、真实发布自动化、复杂编排。
- 输入：`articles/inbox/` 内容、基础配置。
- 输出：数据库记录、计划任务、执行日志。
- 验收标准：四个命令串联执行成功且无阻断异常。
- 建议测试/冒烟命令：`python -m wechat_article_scheduler.cli init-db && python -m wechat_article_scheduler.cli scan && python -m wechat_article_scheduler.cli plan && python -m wechat_article_scheduler.cli run-once`。
- 退出标准：CLI 闭环可重复执行，默认 mock，无真实发布副作用。
- 风险：数据表缺失、内容格式不稳定。
- 回滚点：回退到仅 `init-db` 与只读扫描。
- 交付项：
  - [x] 初始化数据库命令可执行
  - [x] inbox 扫描入库
  - [x] 计划任务生成
  - [x] 到期任务执行
  - [x] 最小工作流测试通过

### Round 1 - 治理轮

- 目标：建立可协作、可审计的治理基线。
- 范围：治理文件、文档重构、安全边界说明。
- 非目标：大规模业务重构。
- 输入：现有代码、文档与目录结构。
- 输出：治理协议、项目卡片、策略文件。
- 验收标准：核心治理文件齐全并可读可用。
- 建议测试/冒烟命令：`python -m pytest tests/test_digest_limits.py tests/test_parser.py tests/test_workflow.py -q`。
- 退出标准：治理入口文件一致，默认 mock 与 secret 禁止规则清晰。
- 风险：文档与实现漂移。
- 回滚点：恢复上一版治理文件并保留增量报告。
- 交付项：
  - [x] 完成仓库审计报告
  - [x] 补齐治理入口文件
  - [x] 统一摘要上限 120
  - [x] 增加基础约束测试
  - [x] 明确 mock 默认模式

### Round 2 - 内容库建模

> 历史说明：本轮最初引入了 `review_status` 审核字段；Phase 10（Round 43）已移除审核概念，仅保留集合、标签与索引能力。

- 目标：明确内容实体与组织维度，支撑后续流程。
- 范围：内容集合、标签、索引、导入批次。
- 非目标：复杂推荐或自动审核。
- 输入：原始文章文件与规则配置。
- 输出：可检索内容库结构。
- 验收标准：内容条目可查询、归类可追踪。
- 建议测试/冒烟命令：`python -m wechat_article_scheduler.cli events --limit 5` 与内容库相关测试。
- 退出标准：文章集合、标签或索引的最小模型不阻断 scan/plan。
- 风险：历史数据兼容性。
- 回滚点：降级到基础文章表 + 事件审计。
- 交付项：
  - [x] 内容库模型落地
  - [x] 标签/集合字段可用
  - [x] 基础查询能力接入
  - [x] 最小数据一致性校验
  - [x] 对应测试覆盖

## Phase 1：产品化 MVP

### Round 3 - 调度域模块化

- 目标：将调度逻辑模块化，降低耦合。
- 范围：scheduler 领域拆分、执行器分层。
- 非目标：改写核心业务语义。
- 输入：现有调度逻辑与任务模型。
- 输出：更清晰的模块边界。
- 验收标准：行为保持一致且测试通过。
- 建议测试/冒烟命令：`python -m pytest tests/test_real_adapter.py tests/test_scheduler_plan.py -q`。
- 退出标准：旧导入路径兼容，调度执行语义不变。
- 风险：拆分后调用链断裂。
- 回滚点：回退到旧调度入口。
- 交付项：
  - [x] scheduler 子模块拆分
  - [x] 执行器职责分离
  - [x] 运行时接口稳定
  - [x] 关键路径回归测试
  - [x] 文档同步更新

### Round 4 - 数据迁移体系

- 目标：建立可升级、可回滚的数据迁移流程。
- 范围：migrations、版本记录、回滚策略。
- 非目标：引入外部迁移平台。
- 输入：现有 SQLite schema。
- 输出：版本化迁移机制。
- 验收标准：迁移与回滚路径可验证。
- 建议测试/冒烟命令：`python scripts/check_repo_contract.py` 与数据库相关测试。
- 退出标准：新旧库均可 init/migrate，迁移记录可追踪。
- 风险：历史库升级失败。
- 回滚点：锁定在已知稳定 schema 版本。
- 交付项：
  - [x] 迁移版本机制
  - [x] 升级脚本可运行
  - [x] 回滚策略文档化
  - [x] 兼容性测试补齐
  - [x] 升级说明落库

### Round 5 - Web 控制台增强

- 目标：提供最小可用后台入口。
- 范围：FastAPI 管理页、基础接口、人工触发。
- 非目标：前端框架化重构。
- 输入：CLI 与数据库状态接口。
- 输出：可访问的本地控制台。
- 验收标准：核心 API 可调用、页面可打开。
- 建议测试/冒烟命令：`python -m pytest tests/test_web_app.py -q`。
- 退出标准：Web 不引入前端构建链，CLI 入口保持可运行。
- 风险：页面能力弱、可用性不足。
- 回滚点：仅保留 API，不保留交互页面。
- 交付项：
  - [x] FastAPI `create_app` 落地
  - [x] `/api/status` 等核心端点
  - [x] 首页触发 scan/plan/run-once
  - [x] 基础 web 测试
  - [x] README 增加 `serve` 入口

### Round 6 - 渲染与模板扩展

- 目标：稳定 Markdown/HTML 渲染策略。
- 范围：渲染规则、模板兼容、解析测试。
- 非目标：完整富文本编辑器。
- 输入：文章正文与摘要字段。
- 输出：可预测的渲染结果。
- 验收标准：渲染与解析测试稳定通过。
- 建议测试/冒烟命令：`python -m pytest tests/test_renderer_markdown.py tests/test_parser.py -q`。
- 退出标准：Markdown/HTML 处理边界文档化，摘要限制不回退。
- 风险：不同内容格式兼容成本。
- 回滚点：降级到最小 Markdown 渲染。
- 交付项：
  - [x] 渲染模块清晰化
  - [x] 模板策略可配置
  - [x] 解析容错加强
  - [x] 渲染回归测试
  - [x] 相关文档补充

## Phase 2：发布可靠性

### Round 7 - 封面资产管理

- 目标：让封面素材管理可追溯、可复用。
- 范围：素材目录、引用关系、人工裁剪流程。
- 非目标：自动图像生成流水线。
- 输入：封面资源文件与文章关联信息。
- 输出：统一资产使用路径。
- 验收标准：素材引用与流程说明完整。
- 建议测试/冒烟命令：封面资产 smoke 当前允许 skip；后续补 `tests/test_cover_assets.py`。
- 退出标准：封面缺失时有明确降级或阻断说明。
- 风险：素材缺失导致发布失败。
- 回滚点：允许无封面回退策略。
- 交付项：
  - [x] 素材目录规范
  - [x] 引用关系说明
  - [x] 人工裁剪流程落文档
  - [x] 资产模块结构固定
  - [x] 可用性自检补充

### Round 8 - 可观测与运维

- 目标：提高失败定位效率与运行透明度。
- 范围：失败分类、重试策略、日志与指标。
- 非目标：外部监控平台强依赖。
- 输入：执行事件、错误日志、重试记录。
- 输出：可检索审计与运维信号。
- 验收标准：失败路径可分类、可重试、可追踪。
- 建议测试/冒烟命令：`python -m pytest tests/test_scheduler_hardening.py -q`。
- 退出标准：失败/重试/DRY_RUN 行为有测试和审计事件。
- 风险：日志噪音与定位成本上升。
- 回滚点：保留关键事件，收敛非必要日志。
- 交付项：
  - [x] 失败分类机制
  - [x] 重试流程加强
  - [x] 审计事件补全
  - [x] 运维相关测试
  - [x] DRY_RUN 行为说明

### Round 9 - 发布工作台产品化

- 目标：形成稳定交付与维护基线。
- 范围：文档收口、流程规范、门控固化。
- 非目标：引入重型工程平台。
- 输入：前序轮次产物。
- 输出：可持续维护的工作台基线。
- 验收标准：核心流程可重复执行，文档与门控一致。
- 建议测试/冒烟命令：`python -m pytest -q` 与 `python scripts/agent_gate.py gate`。
- 退出标准：README、docs/index、agent_gate 与当前轮状态可互相指向。
- 风险：治理文件与代码脱节。
- 回滚点：以 `agent_gate` 与测试结果为准恢复。
- 交付项：
  - [x] 路线图与门控对齐
  - [x] gate 报告机制固定
  - [x] 文档入口统一
  - [x] 当前轮状态可追踪
  - [x] 长期维护说明补齐

## Phase 3：可用性与持续推进

### Round 10 - 基础工作台可用性升级

- 目标：将后台从“可用”提升到“可视化、易操作”。
- 范围：布局优化、交互反馈、状态可读性、轻量样式。
- 非目标：引入 React/Vue、改写后端业务语义。
- 输入：现有 `create_app` 页面与 API。
- 输出：更清晰的工作台界面。
- 验收标准：分区清晰、操作可反馈、失败有建议。
- 建议测试/冒烟命令：`python -m pytest tests/test_web_app.py -q`；可用 TestClient 访问 `/` 与 `/api/overview`。
- 退出标准：首页包含安全状态、操作区、状态卡片、最近任务、事件日志、文档入口；不引入重前端框架。
- 风险：前端逻辑膨胀或与 API 不一致。
- 回滚点：保留 API，回退为简版模板。
- 交付项：
  - [x] 头部/状态区/操作区/结果区布局
  - [x] scan/plan/run-once/status 分组按钮与说明
  - [x] 操作 loading 与防重复点击
  - [x] 成功/失败显著反馈
  - [x] 状态 key-value 展示与 mode 醒目标识
  - [x] 失败下一步建议
  - [x] real 模式风险提示

### Round 11 - 路线图执行化与治理编排

- 目标：让轮次推进“可执行、可验收、可复用”。
- 范围：Phase 分组、轮次模板、门控同步约束。
- 非目标：自动推进当前轮次。
- 输入：`docs/rounds.md`、`agent_gate`、治理文件。
- 输出：结构化路线图与同步规则。
- 验收标准：新增/调整轮次后机器注册表与测试一致。
- 建议测试/冒烟命令：`python -m pytest tests/test_agent_gate.py -q`。
- 退出标准：Round 数量、关键标题、治理 round_range 与协议扩展字段同步。
- 风险：规则过多影响开发效率。
- 回滚点：保留最小必需字段与同步脚本。
- 交付项：
  - [x] 路线图改为 Phase 分组
  - [x] 每轮补齐目标/范围/验收等字段
  - [x] 每轮可勾选交付清单
  - [x] 产出物命名规范明确
  - [x] 文档先行→gate→advance 流程固化
  - [x] ROUND_ORDER/ROUND_META 同步扩展
  - [x] `tests/test_agent_gate.py` 同步校验

### Round 12 - 持续演进与质量门禁强化

- 目标：形成后续可持续推进机制，避免路线图再次潦草。
- 范围：轮次健康检查、测试覆盖提醒、文档 drift 检查。
- 非目标：替代人工评审。
- 输入：现有 gate、测试与报告体系。
- 输出：后续轮次推进的质量护栏。
- 验收标准：新增轮次时可被脚本与测试及时发现不一致。
- 建议测试/冒烟命令：`python -m pytest tests/test_agent_gate.py -q && python scripts/agent_gate.py status`。
- 退出标准：文档一致性检查覆盖 Round 标题、数量、必填字段和报告模板。
- 风险：门禁过严导致推进阻塞。
- 回滚点：保留核心一致性检查，降级非关键检查。
- 交付项：
  - [x] 评估新增 rounds 文档一致性检查脚本
  - [x] 增加 round 报告模板使用约束
  - [x] 增加关键轮次最小 smoke 建议集
  - [x] 增加未覆盖测试提醒机制
  - [x] 规划 round_013+ 的候选池

## Phase 4：内容生产能力

### Round 13 - Renderer 内容渲染深化

- 目标：让文章正文从“可发布”提升到“可预览、可解释、可回归”。
- 范围：Markdown/HTML 规则矩阵、摘要/标题兜底、预览接口、渲染 fixture。
- 非目标：富文本编辑器、前端拖拽排版、自动改写文章内容。
- 输入：文章正文、摘要、现有 `renderers/` 与 parser。
- 输出：稳定渲染策略、预览样例、回归测试。
- 验收标准：常见 Markdown 段落、标题、列表、链接、图片占位可预测渲染。
- 建议测试/冒烟命令：`python -m pytest tests/test_renderer_markdown.py tests/test_parser.py -q`。
- 退出标准：渲染失败能给出可读错误或降级结果，不影响 scan/plan/run-once。
- 风险：过度追求排版导致范围膨胀。
- 回滚点：降级为 Round 6 最小 Markdown 渲染。
- 交付项：
  - [x] 渲染规则矩阵文档
  - [x] HTML/Markdown fixture 覆盖
  - [x] Web 草稿预览只读入口
  - [x] 摘要/标题兜底测试
  - [x] 渲染失败降级说明

### Round 14 - Cover 封面资产工作流

- 目标：让封面素材从目录规范变为可检查、可关联的工作流。
- 范围：封面文件索引、文章关联、缺失提示、人工裁剪说明、Web 只读展示。
- 非目标：自动生成封面、在线图片编辑器、商业素材库。
- 输入：`cover_assets/`、文章元数据、默认 thumb 配置。
- 输出：封面资产索引与发布前检查。
- 验收标准：缺封面、路径无效、默认封面使用都能被检测并提示。
- 建议测试/冒烟命令：后续补 `python -m pytest tests/test_cover_assets.py -q`。
- 退出标准：真实发布前能明确知道封面是否可用。
- 风险：素材路径与本地文件移动不一致。
- 回滚点：允许无封面或默认封面策略继续运行。
- 交付项：
  - [x] 封面索引模型
  - [x] 缺失/无效路径检查
  - [x] Web 只读封面状态
  - [x] 人工裁剪流程更新
  - [x] 发布前封面 smoke

### Round 15 - Content Library 与多合集

- 目标：支持本地内容库按合集、标签和状态组织，避免文章越多越难管理。
- 范围：合集元数据、文章归属、状态筛选、Web 只读筛选、CLI 查询增强。
- 非目标：多人协作 CMS、权限系统、云同步。
- 输入：articles 表、content_library 现有骨架、样稿目录。
- 输出：可查询的合集/标签/状态视图。
- 验收标准：同一文章可被稳定归类，scan/plan 不破坏已有合集信息。
- 建议测试/冒烟命令：后续补 `python -m pytest tests/test_content_library.py -q`。
- 退出标准：多合集规划有最小数据结构和查询测试。
- 风险：过早建模导致迁移负担。
- 回滚点：保留 articles 基础状态，合集字段可为空。
- 交付项：
  - [x] 合集元数据设计
  - [x] 标签/状态筛选
  - [x] CLI 查询入口
  - [x] Web 只读列表增强
  - [x] scan/plan 回归测试

## Phase 5：发布编排与真实能力

### Round 16 - Scheduler 编排与人工闸门

> 历史说明：本轮最初以 `review_status=approved` 作为真实发布闸门；Phase 10（Round 43/46）已改为「默认演练 + 显式开关 + 执行到点二次确认 + 预检清单」，不再依赖审核状态。

- 目标：让发布调度具备更明确的执行前检查与人工确认闸门。
- 范围：run-once 执行前检查、重试策略可视化、队列筛选、真实发布显式开关。
- 非目标：后台常驻服务大重构、分布式调度、内容审批流。
- 输入：publish_jobs、events、现有 scheduler runtime。
- 输出：更安全的本地发布编排。
- 验收标准：未经确认/未开启真实发布开关时不会真的发布，mock 路径仍便于测试。
- 建议测试/冒烟命令：`python -m pytest tests/test_scheduler_hardening.py -q` 与新增闸门测试。
- 退出标准：执行闸门行为写入文档、CLI 与 Web 提示一致。
- 风险：状态机复杂化影响现有 run-once。
- 回滚点：回退到 pending/running/done/failed 基础状态。
- 交付项：
  - [x] 真实发布显式开关
  - [x] run-once 闸门测试
  - [x] Web 队列筛选
  - [x] 重试状态说明
  - [x] 事件审计补充

### Round 17 - 真实发布安全试运行

- 目标：在默认关闭真实发布的前提下，定义可审计的 real draft / real publish 试运行流程。
- 范围：real draft-only smoke、WECHAT_ENABLE_PUBLISH 明确提示、发布前检查清单、失败归因。
- 非目标：默认启用真实发布、模拟网页登录、保存 cookie、绕过官方 API。
- 输入：RealWechatAdapter、环境变量、封面与渲染结果。
- 输出：真实 API 试运行手册与可选择的受控测试。
- 验收标准：没有授权和显式开关时不会触发真实发布；授权后也有人工检查点。
- 建议测试/冒烟命令：默认只跑 mock 单测；真实 API 测试需人工设置独立开关。
- 退出标准：真实发布风险、回滚、日志脱敏和失败处理均文档化。
- 风险：误配置导致真实发布。
- 回滚点：强制回到 WECHAT_MODE=mock / WECHAT_ENABLE_PUBLISH=false。
- 交付项：
  - [ ] real draft-only 检查清单
  - [ ] 发布前安全提示
  - [ ] 真实 API 测试开关说明
  - [ ] 失败归因与重试文档
  - [ ] 日志脱敏回归测试

### Round 18 - 能力矩阵与 AI 辅助入口

- 目标：把项目能力、限制和 AI 可辅助事项整理成可维护矩阵，指导后续小步推进。
- 范围：微信能力矩阵、AI 辅助摘要/检查入口规划、治理报告模板、未来 Round 候选池。
- 非目标：自动生成并发布文章、调用付费模型、替代人工审核。
- 输入：`docs/wechat_capability_matrix.md`、路线图、Web/CLI 现状。
- 输出：能力矩阵、AI 辅助边界、后续候选 Round。
- 验收标准：每项能力明确“已实现/可 mock/需人工/未来/暂不做”。
- 建议测试/冒烟命令：`python -m pytest tests/test_agent_gate.py -q` 与文档一致性检查。
- 退出标准：后续 Agent 能按矩阵选择小任务，不再把大目标塞进单轮。
- 风险：AI 辅助边界不清导致过度自动化。
- 回滚点：保留手工文档矩阵，不接入自动辅助。
- 交付项：
  - [ ] 能力矩阵状态更新
  - [ ] AI 辅助边界文档
  - [ ] 未来 Round 候选池
  - [ ] 治理报告模板强化
  - [ ] “暂不做”清单维护

## Phase 6：普通用户视图与主流程

> 贯穿主题：目标用户是完全不懂编程的个人用户，主要使用场景是电脑浏览器中的本地工作台。普通视图默认只回答四个问题：现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办。技术元数据、原始 JSON、数据库路径、内部字段默认进入“高级信息”开关或调试页。
> 每一轮仍坚持 **Desktop-first local workbench**：优先服务桌面端信息密度、批量处理效率和清晰操作路径；手机/平板只做响应式兼容，不把窄屏作为默认形态。
> 保持轻量（FastAPI + 服务端渲染 / 原生少量 JS），不引入 React/Vue。诊断依据见 `docs/web_console_usability_review.md` 与 `docs/web_console_design.md`。

### Round 19 - 普通用户工作台原则与 Playwright 视觉基线

- 目标：把“普通用户模式优先、桌面浏览器优先、高级信息默认隐藏”固化成后续 Web 轮次的验收地基。
- 范围：Playwright 开发依赖、`tools/browser_automation/ui_review.py` 诊断脚本、桌面 1280 基线截图、空状态截图、普通/详情/高级三层信息边界清单。
- 非目标：实现完整 UI 改版或编写大量端到端断言（留到 Round 35）。
- 输入：现有 `create_app` 与 `cli serve`、`articles/imported/` 样稿、当前 Web 首页。
- 输出：截图基线（`docs/reports/ui_review/`）、DOM 快照、普通用户工作台原则文档。
- 验收标准：诊断脚本可复跑；报告明确普通视图不得裸露技术字段；桌面是主验收对象，窄屏是兼容验收。
- 建议测试/冒烟命令：`.venv/bin/python tools/browser_automation/ui_review.py --seed 5` 与 `--seed 0`。
- 退出标准：后续 Agent 能根据基线判断“普通用户是否看得懂”，而不是只判断页面能否打开。
- 风险：截图被当成功能验收替代真实体验改造。
- 回滚点：保留诊断脚本，不纳入强制 gate。
- 交付项：
  - [x] Playwright 作为开发依赖记录
  - [x] 桌面主基线、空状态基线、窄屏兼容截图
  - [x] 普通/详情/高级三层信息边界清单
  - [x] 普通用户视角诊断报告
  - [x] 复跑使用说明

### Round 20 - 术语人话化与中文文案标准

- 目标：建立“内部名 → 普通用户说法”的统一映射，让普通视图不再直接暴露工程术语。
- 范围：术语映射模块/字典、状态枚举中文化、用户文案标准、裸英文枚举检查。
- 非目标：改动数据库字段名或接口字段名（仅展示层翻译）。
- 输入：`docs/web_console_usability_review.md` 术语对照表、现有状态字段。
- 输出：可复用中文文案映射、UI 文案准则、首屏状态中文化。
- 验收标准：普通视图不出现 `imported`、`pending`、`mock`、`publish_jobs` 等裸内部词；高级区允许显示内部名但要标注“调试用”。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：新增状态或按钮时有明确补充术语映射的位置。
- 风险：翻译不一致导致同一状态多种叫法。
- 回滚点：保留英文枚举为高级区兜底。
- 交付项：
  - [x] 术语映射单一来源
  - [x] 状态枚举中文化
  - [x] UI 文案标准
  - [x] 普通视图裸内部词检查
  - [x] 对应 web 测试

### Round 21 - 普通视图信息减法

- 目标：从首屏移除普通用户不需要的内部信息，只留下可行动的少量信息。
- 范围：隐藏数据库绝对路径、原始 JSON、内部统计字段、技术开关原文；普通视图只保留安全状态、待办数量、最近结果和下一步。
- 非目标：删除调试能力或改变后端接口返回结构。
- 输入：`/api/status`、`/api/overview`、当前首页卡片和结果区。
- 输出：普通视图首屏减法清单与实现，技术内容迁移到高级区占位。
- 验收标准：首屏默认不出现数据库路径、`processed`、`skipped_future`、`payload_json`、原始 JSON 等内容。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：所有被隐藏的信息仍能通过高级区或调试页设计找到，不影响排错。
- 风险：隐藏过度导致失败时缺少线索。
- 回滚点：在高级区恢复原始信息展示。
- 交付项：
  - [x] 首屏无数据库路径和原始 JSON
  - [x] 内部统计字段默认隐藏
  - [x] 普通视图只保留四类核心信息
  - [x] 高级区占位说明
  - [x] 对应 web 测试

### Round 22 - 三步操作主流程

- 目标：让用户一眼知道先点什么、后点什么、每一步会发生什么。
- 范围：把 scan/plan/run-once 组织成“1 找文章 → 2 安排时间 → 3 执行到点文章”的主流程，刷新状态降为次要操作。
- 非目标：新增业务能力或改变 CLI 语义。
- 输入：现有四个按钮、CLI 触发接口、普通用户文案标准。
- 输出：带步骤编号、说明和安全提示的主操作区。
- 验收标准：桌面首屏能看到三步主流程；每个按钮旁都有一句普通用户能理解的解释；刷新状态不混入主流程。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：操作顺序与实际 scan/plan/run-once 行为一致。
- 风险：步骤文案过度简化导致用户误解真实发布风险。
- 回滚点：回退为基础按钮组，保留文案映射。
- 交付项：
  - [x] 三步编号和说明
  - [x] 主操作与次操作分层
  - [x] 每步安全说明
  - [x] 桌面首屏可见
  - [x] 对应 web 测试

### Round 23 - 人话反馈系统

- 目标：点完按钮后给用户“做成了什么、没做成什么、下一步是什么”的明确反馈。
- 范围：scan/plan/run-once 成功摘要、失败摘要、下一步建议；原始字段仅进入高级区。
- 非目标：改变后端接口结构或隐藏严重错误。
- 输入：scan/plan/run-once 返回值、事件记录、术语映射。
- 输出：人话反馈生成器或展示层规则。
- 验收标准：成功时显示“已收录 X 篇新文章”“已安排 X 篇待发布”等；失败时显示原因、影响和下一步。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：内部字段（如 `skipped_future`）不裸露，但能转成普通说法（如“还没到发布时间”）。
- 风险：人话摘要丢失排错细节。
- 回滚点：高级区保留原始响应。
- 交付项：
  - [x] scan 人话摘要
  - [x] plan 人话摘要
  - [x] run-once 人话摘要
  - [x] 失败原因与下一步
  - [x] 对应 web 测试

### Round 24 - 空状态与首次使用

- 目标：第一次打开、没有文章、没有任务、没有事件时也知道该怎么开始。
- 范围：各区块空状态、首次使用引导、示例路径说明、关键名词“这是什么”提示。
- 非目标：完整弹窗向导或在线教程。
- 输入：空数据库首页、`articles/inbox/` 约定、用户手册。
- 输出：空状态友好文案与首次使用引导。
- 验收标准：空库下首页不出现“暂无 publish_jobs”等技术腔，改为“还没有待发布文章，请先把文章放进收件箱，再点扫描”。
- 建议测试/冒烟命令：`.venv/bin/python tools/browser_automation/ui_review.py --seed 0` 与 `.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：空状态每条都有明确下一步，不堆叠过多解释。
- 风险：提示过多造成干扰。
- 回滚点：保留简单空状态文案。
- 交付项：
  - [x] 首页空状态
  - [x] 文章列表空状态
  - [x] 发布队列空状态
  - [x] 事件日志空状态
  - [x] 空库截图基线

### Round 25 - 安全发布护栏

- 目标：避免普通用户误触真实发布，让“现在不会真发”始终清楚可见。
- 范围：运行模式人话化、真实发布二次确认、演练/真实视觉区分、危险操作文案。
- 非目标：改变默认 mock 与 `WECHAT_ENABLE_PUBLISH=false` 的安全默认值。
- 输入：当前模式、发布开关、run-once 触发入口。
- 输出：安全状态条、真实发布确认流程、风险提示。
- 验收标准：mock 模式不打扰；real draft-only 明确说明只创建草稿；真实发布前必须确认。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：普通用户能在首屏判断“会不会真的发到公众号”。
- 风险：确认逻辑误判模式或被绕过。
- 回滚点：强制隐藏真实发布按钮，仅保留 mock/草稿。
- 交付项：
  - [x] 运行模式人话化
  - [x] 真实发布二次确认
  - [x] 演练/真实视觉区分
  - [x] 危险文案与下一步提示
  - [x] 对应 web 测试

## Phase 7：桌面工作台信息架构

### Round 26 - 桌面主布局

- 目标：建立电脑浏览器优先的工作台骨架，避免所有内容线性堆在一个窄列里。
- 范围：顶部安全状态、左侧导航或分区导航、主内容区、次级内容区、高级信息入口；窄屏仅保证堆叠可读。
- 非目标：引入前端框架或完整设计系统。
- 输入：现有首页区块、普通视图四问题原则、桌面 1280 截图。
- 输出：桌面主布局骨架。
- 验收标准：1280 宽桌面首屏能定位概览、主操作、最近结果和待办摘要；技术信息不挤占主区。
- 建议测试/冒烟命令：`.venv/bin/python tools/browser_automation/ui_review.py --seed 5`。
- 退出标准：桌面端不为手机卡片化牺牲信息密度；窄屏无整页横向溢出。
- 风险：布局重排导致功能难找。
- 回滚点：回退到分区堆叠布局。
- 交付项：
  - [x] 顶部安全状态
  - [x] 桌面导航结构
  - [x] 主内容区与次级内容区
  - [x] 高级入口位置
  - [x] 三视口截图基线

### Round 27 - 文章列表普通化

- 目标：让文章列表展示用户真正关心的信息，而不是文件和数据库元数据。
- 范围：标题、合集、章节号、状态、摘要长度、是否有封面、导入时间、更新时间；隐藏 hash、绝对路径、内部 id 等。
- 非目标：完整多合集导入或富文本编辑。
- 输入：articles 表、内容库设计、现有 Web 查询能力。
- 输出：普通用户可读的文章列表视图。
- 验收标准：用户能快速判断哪些文章已收录、哪些缺封面/摘要、哪些准备发布；技术字段默认隐藏。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：高级区仍可查内部 id/路径，普通列表不显示。
- 风险：当前数据库字段不足以展示完整信息。
- 回滚点：保留最小标题 + 状态列表。
- 交付项：
  - [x] 文章列表列优先级
  - [x] 中文状态与颜色
  - [x] 缺封面/摘要提示
  - [x] 技术字段默认隐藏
  - [x] 对应 web 测试

### Round 28 - 发布队列普通化

- 目标：让发布队列回答“哪篇文章、什么时候、现在怎样、我能做什么”。
- 范围：任务标题、计划时间、中文状态、失败原因、可操作建议；隐藏 `retry_count` 等技术列。
- 非目标：实现复杂拖拽排期或批量编辑。
- 输入：`publish_jobs`、`events`、调度状态。
- 输出：普通用户可读的发布队列。
- 验收标准：队列表格默认不显示 `publish_jobs`、`retry_count`、内部 id 等技术词；失败任务有人话原因。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：高级区能展开查看原始任务详情。
- 风险：隐藏重试次数后定位失败不方便。
- 回滚点：高级区保留技术列。
- 交付项：
  - [x] 队列列优先级
  - [x] 中文状态与颜色
  - [x] 失败原因和建议
  - [x] 技术列默认隐藏
  - [x] 对应 web 测试

### Round 29 - 事件日志时间线

- 目标：把事件日志从“调试记录表”改成普通人可读的操作时间线。
- 范围：事件类型中文化、人话摘要、时间相对显示、原始 payload 下沉高级区。
- 非目标：改变事件存储结构或删除审计信息。
- 输入：`events` 表、术语映射、当前事件展示。
- 输出：可扫读的事件时间线。
- 验收标准：普通视图显示“刚刚收录了《第 2 章》”“已创建公众号草稿”等；不直接显示 `payload_json`。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：审计完整性不下降，原始事件仍可在高级区查看。
- 风险：人话摘要与原始事件不一致。
- 回滚点：高级区保留原始事件表。
- 交付项：
  - [x] 事件类型中文化
  - [x] 人话事件摘要
  - [x] 时间线展示
  - [x] payload 默认隐藏
  - [x] 对应 web 测试

### Round 30 - 高级信息开关

- 目标：让开发者和 Agent 仍能查看技术细节，但普通用户默认看不到。
- 范围：统一高级信息开关或 `/debug` 页，收纳数据库路径、原始 JSON、内部统计、内部 id、事件 payload、英文枚举。
- 非目标：暴露任何 secret、token、cookie 或 `.env` 内容。
- 输入：被 Round 21/27/28/29 下沉的全部技术信息。
- 输出：集中、默认隐藏、带敏感信息保护的高级视图。
- 验收标准：普通视图无原始 JSON；高级区不打印 secret；高级区入口文案说明“排错用”。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：普通用户不会被技术字段打扰，Agent 排错仍有入口。
- 风险：高级区误暴露敏感信息。
- 回滚点：移除高级区，仅保留后端日志与测试。
- 交付项：
  - [x] 高级信息开关或 `/debug` 页
  - [x] 原始 JSON 与内部统计归位
  - [x] 数据库路径仅在高级区
  - [x] secret 不出现校验
  - [x] 对应 web 测试

## Phase 8：体验固化与后续接入规范

### Round 31 - 帮助与解释系统

- 目标：让用户不用读源码也能理解关键操作和关键名词。
- 范围：内嵌帮助/术语面板、关键操作旁说明、用户手册入口、短句式说明。
- 非目标：在线客服、复杂教程或外部知识库。
- 输入：术语对照表、`docs/user_manual.md`、普通视图文案。
- 输出：应用内帮助入口与名词解释。
- 验收标准：用户能从首屏找到“这是什么/该怎么做”的解释；帮助内容与术语标准一致。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py -q`。
- 退出标准：帮助文案不替代主流程，主流程仍能一眼看懂。
- 风险：帮助内容与实现漂移。
- 回滚点：回退为静态文档链接。
- 交付项：
  - [x] 内嵌帮助入口
  - [x] 关键操作旁说明
  - [x] 用户手册链接
  - [x] 帮助内容一致性检查
  - [x] 对应 web 测试

### Round 32 - 错误与恢复指引

- 目标：失败时用普通用户语言说明原因、影响和下一步。
- 范围：扫描失败、排期失败、草稿创建失败、摘要截断、到点任务未执行、配置缺失等常见错误的人话说明。
- 非目标：完整自动修复系统。
- 输入：异常、events、adapter 错误码、digest warning。
- 输出：错误归因与恢复建议映射。
- 验收标准：用户看到失败时知道“发生了什么、影响什么、下一步点什么或改什么”。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py tests/test_digest_limits.py -q`。
- 退出标准：原始错误仍在高级区，普通视图不显示堆栈或未解释字段。
- 风险：错误被过度简化。
- 回滚点：高级区保留原始错误和堆栈摘要。
- 交付项：
  - [x] 常见错误人话映射
  - [x] 影响说明
  - [x] 下一步建议
  - [x] 原始错误下沉高级区
  - [x] 对应测试

### Round 33 - 桌面效率优化

- 目标：在电脑浏览器里提升批量管理效率，而不是把页面做成手机看板。
- 范围：筛选、排序、状态颜色、列表密度、固定表头或简易分组、最近操作定位。
- 非目标：复杂数据表格组件或前端框架。
- 输入：文章列表、发布队列、事件时间线。
- 输出：桌面高效扫读与定位能力。
- 验收标准：1280 宽桌面能高效比较多条文章/任务；常用筛选不需要看内部字段。
- 建议测试/冒烟命令：`.venv/bin/python tools/browser_automation/ui_review.py --seed 5`。
- 退出标准：桌面效率提升不破坏窄屏基本可读。
- 风险：筛选状态与后端数据不一致。
- 回滚点：保留基础表格。
- 交付项：
  - [x] 队列筛选/排序
  - [x] 文章筛选/排序
  - [x] 状态颜色统一
  - [x] 桌面信息密度调优
  - [x] 截图基线更新

### Round 34 - 窄屏兼容验收

- 目标：明确手机/平板只是兼容目标，保证不坏、不溢出、能点、能读。
- 范围：375/768 视口无整页横向溢出、关键按钮可点、文字可读、导航可达。
- 非目标：把手机做成默认看板或牺牲桌面表格密度。
- 输入：Playwright 三视口截图、桌面主布局。
- 输出：窄屏兼容验收清单和必要 CSS 修复。
- 验收标准：375/768 视口 `scrollWidth <= clientWidth`，主操作可达，内容顺序可读。
- 建议测试/冒烟命令：`.venv/bin/python tools/browser_automation/ui_review.py --seed 5`。
- 退出标准：窄屏兼容不改变桌面优先原则。
- 风险：为窄屏过度重排导致桌面退化。
- 回滚点：只保留容器内滚动和断行。
- 交付项：
  - [x] 375 视口兼容
  - [x] 768 视口兼容
  - [x] 主操作可点
  - [x] 整页无横向溢出
  - [x] 兼容验收报告

### Round 35 - Playwright E2E 可用性基线

- 目标：把普通用户友好结论变成可自动回归的测试。
- 范围：普通视图不裸露内部字段、三步流程可见、安全状态可读、桌面首屏清晰、窄屏无整页横向溢出。
- 非目标：像素级视觉对比或 CI 基础设施改造。
- 输入：`ui_review.py` 与各轮可用性产物。
- 输出：可复跑的端到端可用性测试。
- 验收标准：关键断言可本地运行；无浏览器环境优雅 skip。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_ui_e2e.py -q`。
- 退出标准：测试稳定，能防止后续 Agent 把内部字段重新放回普通视图。
- 风险：端到端测试不稳定。
- 回滚点：保留诊断脚本，移除强制断言。
- 交付项：
  - [x] 普通视图字段断言
  - [x] 三步流程断言
  - [x] 安全状态断言
  - [x] 窄屏无溢出断言
  - [x] 无浏览器环境 skip

### Round 36 - 非技术用户走查报告

- 目标：按“完全不懂编程的人”的视角完成一次桌面浏览器走查。
- 范围：安全理解、主流程理解、反馈理解、错误恢复、信息是否过多、术语是否友好。
- 非目标：引入新功能。
- 输入：Round 19–35 的全部产物、截图、测试结果。
- 输出：非技术用户走查报告与遗留清单。
- 验收标准：每个核心场景都有“看得懂/做得到/知道结果/知道下一步”的结论。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest -q` 与 `.venv/bin/python tools/browser_automation/ui_review.py --seed 5`。
- 退出标准：遗留问题明确进入后续候选轮，不再用工程术语掩盖体验问题。
- 风险：走查结论主观。
- 回滚点：保留问题清单，继续分批整改。
- 交付项：
  - [x] 非技术用户走查清单
  - [x] 核心场景验收结论
  - [x] 遗留问题分级
  - [x] 截图归档
  - [x] 走查报告

### Round 37 - Web 控制台 MVP 收口

- 目标：冻结普通视图信息架构，让 Web 控制台达到“个人可日常使用”的 MVP 状态。
- 范围：Round 19–36 遗留项收口、普通/详情/高级边界冻结、用户手册同步、截图更新。
- 非目标：新增大功能，如完整封面裁剪、多合集复杂排期或自动发布。
- 输入：走查报告、E2E 测试、用户手册。
- 输出：Web 控制台 MVP 收口报告。
- 验收标准：普通用户能完成扫描、排期、执行演练/草稿路径，并理解状态与失败提示。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest -q` 与 `.venv/bin/python scripts/agent_gate.py gate`。
- 退出标准：MVP 边界清晰，未实现能力不混在普通视图里。
- 风险：把未来功能提前塞进 MVP。
- 回滚点：保留当前稳定普通视图，延期未完成体验项。
- 交付项：
  - [x] MVP 信息架构冻结
  - [x] 遗留项收口
  - [x] 用户手册同步
  - [x] 截图基线更新
  - [x] MVP 收口报告

### Round 38 - 后续功能接入规范

- 目标：规定未来 Renderer、Cover、Content Library、Scheduler、真实发布等功能接入 Web 时，必须先定义普通视图和高级字段归属。
- 范围：功能接入模板、普通/详情/高级字段清单模板、验收模板、agent_gate 检查建议。
- 非目标：实现这些未来功能本身。
- 输入：Round 19–37 的信息分层经验、现有功能路线图。
- 输出：后续 Web 功能接入规范。
- 验收标准：新增功能不得直接把内部字段放到首屏；必须说明普通用户看什么、高级区看什么、错误怎么解释。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_agent_gate.py -q`。
- 退出标准：后续 Agent 有模板可依，不再把工程字段直接堆到页面。
- 风险：规范过重导致推进变慢。
- 回滚点：保留简化模板，只约束普通视图。
- 交付项：
  - [x] Web 功能接入模板
  - [x] 普通/详情/高级字段清单模板
  - [x] 错误解释模板
  - [x] 未来功能验收模板
  - [x] 治理文档同步

## Phase 9：维护与生产加固

> 在 Round 38 接入规范基础上，补齐发布可靠性与人话 UX 的遗留项；仍保持 Desktop-first、默认 mock、普通视图不裸露内部字段。

### Round 39 - Web 发布前确认入口

> 历史说明：本轮最初实现的是「Web 审核闸门」（标记通过/待审/驳回）；Phase 10（Round 43）移除审核概念后，该入口重构为「发布前确认入口」——上传即待发布，发布前在 Web 给出可读确认与预检提示。

- 目标：让普通用户能在 Web 工作台清楚知道"现在执行会发生什么"，并在真实发布前确认。
- 范围：发布前确认提示、待发布列表、人话状态标签、与 scheduler 执行闸门一致。
- 非目标：内容审批流、多人权限系统。
- 输入：`publish_jobs`、现有 content_library 仓库。
- 输出：Web 发布前确认入口与预检提示。
- 验收标准：执行到点前给出可读确认；真实发布需显式开关与确认；普通视图不裸露内部枚举。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_scheduler_hardening.py tests/test_web_round39_plus.py -q`。
- 退出标准：确认提示与 run-once 执行行为一致。
- 风险：误触发真实发布。
- 回滚点：隐藏 Web 真实发布入口，仅保留演练/草稿。
- 交付项：
  - [x] 发布前确认提示
  - [x] 概览待发布列表
  - [x] 人话发布状态标签
  - [x] 与 scheduler 闸门测试
  - [x] 普通视图发布确认区块

### Round 40 - 定时发布 UX

- 目标：让用户在概览与队列中读懂「下一篇什么时候发」。
- 范围：计划时间人话格式化、下一篇摘要、到点任务提示。
- 非目标：拖拽改期、日历组件。
- 输入：`publish_jobs.scheduled_at`、overview API。
- 输出：`schedule_summary` 与队列 `scheduled_at_label`。
- 验收标准：普通视图显示「YYYY年MM月DD日 HH:MM」；有到点任务时提示可读。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_round39_plus.py tests/test_web_ordinary_copy.py -q`。
- 退出标准：ISO 时间不再直接出现在普通视图表格。
- 风险：时区误解。
- 回滚点：保留 ISO 到高级区。
- 交付项：
  - [x] format_scheduled_at 辅助
  - [x] `/api/schedule-summary`
  - [x] 概览下一篇横幅
  - [x] 队列人话时间列
  - [x] 对应测试

### Round 41 - 真实发布预检清单

- 目标：真实模式执行到点前展示可读检查项。
- 范围：预检 API、模式/审核/封面/摘要检查、确认对话框提示。
- 非目标：自动修复、联网校验。
- 输入：配置、待发布任务、文章摘要。
- 输出：`/api/publish-preflight` 与人话摘要。
- 验收标准：mock 模式提示演练；real 模式列出阻断/提示项。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_round39_plus.py tests/test_web_app.py -q`。
- 退出标准：未批准任务在 real 模式被标记为需处理。
- 风险：预检遗漏真实风险。
- 回滚点：仅保留二次确认。
- 交付项：
  - [x] build_publish_preflight
  - [x] GET `/api/publish-preflight`
  - [x] 执行到点确认附带预检提示
  - [x] overview 嵌入 preflight
  - [x] 对应测试

### Round 42 - 能力矩阵维护

- 目标：同步能力矩阵与已实现功能，固化 Phase 9 维护入口。
- 范围：更新 `docs/wechat_capability_matrix.md`、治理 round_range、gate 注册表。
- 非目标：新业务能力。
- 输入：Round 39–41 产物、现有矩阵。
- 输出：矩阵状态更新与 Round 43+ 候选说明。
- 验收标准：审核闸门、Web 预检、定时 UX 在矩阵中标记为已实现/部分实现。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_agent_gate.py -q`。
- 退出标准：矩阵与代码无显著漂移。
- 风险：文档再次滞后。
- 回滚点：保留矩阵历史行。
- 交付项：
  - [x] 能力矩阵更新
  - [x] Phase 9 路线图同步
  - [x] agent_gate ROUND_ORDER 扩展
  - [x] 治理 round_range 更新
  - [x] gate 测试通过

## Phase 10：产品重定位——批量发布工作台

> 主题：把项目从"带审核的调度器"重定位为"本地作品 → 公众号的批量发布工作台"。用户从网页批量上传作品与封面，上传即视为想发布的内容，没有审核步骤；安全靠默认演练 + 显式开关 + 二次确认 + 预检。仍保持 Desktop-first、默认 mock、普通视图不裸露内部字段。

### Round 43 - 产品重定位与审核概念移除

- 目标：彻底移除"审核 / review_status"概念，确立"上传即发布"的产品叙事与数据模型。
- 范围：迁移删除 `articles.review_status`、清理 content_library / scheduler / web / 文案中的审核逻辑、改写历史轮审核表述、重写路线图与治理注册表。
- 非目标：实现上传/UI（见 Round 44/45）、引入新发布能力。
- 输入：现有 `review_status` 相关代码、`docs/rounds.md`、`scripts/agent_gate.py`、治理文件。
- 输出：无审核字段的数据模型、去审核化路线图、同步的机器注册表与测试。
- 验收标准：全仓 `src/` 无 `review_status` 引用；`init-db` 后 articles 表无该列；scan/plan/run-once 与 mock 路径不受影响。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_migrations.py tests/test_content_library.py tests/test_scheduler_hardening.py -q`。
- 退出标准：审核相关读写门禁全部移除，真实发布安全改由开关 + 确认 + 预检承担。
- 风险：删列需重建/迁移，老库兼容。
- 回滚点：保留迁移文件，可恢复 002 的列定义。
- 交付项：
  - [x] 迁移 `004_drop_review_status.sql`
  - [x] content_library / scheduler / web 去审核
  - [x] 用户文案移除审核标签
  - [x] 路线图与 `ROUND_ORDER`/`ROUND_META`/测试同步
  - [x] 历史轮审核表述改写

### Round 44 - 网页批量上传作品与封面

- 目标：让用户直接在网页**批量上传文章与封面**，不必手动往收件箱拷文件。
- 范围：`python-multipart` 依赖、`articles.cover_path` 迁移、`POST /api/upload` 多文件上传、文章入收件箱并入库、封面入 `articles/covers/` 并按文件名配对、封面静态访问、真实适配器优先使用每篇封面。
- 非目标：在线富文本编辑、图片裁剪、云素材库。
- 输入：用户选择的多个文章文件与封面图、现有 scan / parser / adapter。
- 输出：上传接口、每篇作品独立封面、上传后的人话反馈。
- 验收标准：一次可上传多篇文章与多张封面；同名封面自动绑定到对应文章；mock 全流程可发布；封面可在工作台预览。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_upload.py -q`。
- 退出标准：上传失败有可读提示；上传不破坏既有 scan/plan/run-once。
- 风险：大文件/异常格式、文件名冲突。
- 回滚点：保留 CLI 收件箱扫描入口作为兜底。
- 交付项：
  - [x] `python-multipart` 依赖
  - [x] 迁移 `005_article_cover_path.sql`
  - [x] `POST /api/upload` 与 `web/uploads.py`
  - [x] 每篇封面绑定与静态访问
  - [x] `tests/test_web_upload.py`

### Round 45 - 工作台界面与配色重构

- 目标：把杂乱的多区块页面重做成清爽、现代、以"作品库"为中心的桌面工作台。
- 范围：重写 `admin_template.html`（现代配色、左侧导航、顶部安全状态条、拖拽批量上传区、作品库卡片网格含封面缩略图、发布队列与操作记录）、移除审核区块、保留高级信息开关与 `/debug`、同步 `user_copy` 文案口径。
- 非目标：引入 React/Vue 或前端构建链。
- 输入：上传接口、overview / articles API、普通视图四问题原则。
- 输出：现代化单文件工作台界面。
- 验收标准：首屏即作品库与上传区；桌面 1280 信息密度高；普通视图不裸露内部字段；窄屏无整页横向溢出。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_ordinary_copy.py -q`。
- 退出标准：旧"文章审核"区块彻底移除，关键导航与按钮可用。
- 风险：配色/布局回归影响可读性。
- 回滚点：保留旧模板备份语义，可回退到分区堆叠布局。
- 交付项：
  - [x] 现代配色与左导航
  - [x] 拖拽批量上传区
  - [x] 作品库网格 + 封面缩略图
  - [x] 移除审核区块
  - [x] 高级信息 / debug 保留

### Round 46 - 发布确认护栏与能力矩阵收口

- 目标：用"发布前二次确认 + 预检清单"替代审核门禁，并同步文档与测试收口本次重定位。
- 范围：发布前确认与预检（封面/摘要/标题/模式）、更新 `docs/wechat_capability_matrix.md` / `README.md` / `docs/user_manual.md`、修正受影响测试与治理范围字段。
- 非目标：新增业务能力。
- 输入：Round 43–45 产物、现有预检与测试。
- 输出：一致的发布护栏、更新后的文档与全绿测试。
- 验收标准：真实发布前展示可读检查项；mock 模式提示演练；文档与代码无审核残留；`agent_gate gate` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_agent_gate.py tests/test_web_round39_plus.py -q`。
- 退出标准：能力矩阵与已实现能力一致，后续可在此基础规划 Round 47+。
- 风险：文档滞后于代码。
- 回滚点：保留矩阵历史行。
- 交付项：
  - [x] 发布前确认 + 预检
  - [x] 能力矩阵更新
  - [x] README / user_manual 同步
  - [x] 受影响测试修正
  - [x] 治理范围字段更新

## Phase 11：内容发布正确性与管理能力

> 主题：在批量发布工作台基础上，修正真实草稿与预览的一致性问题，补齐作品删除/回收站生命周期，并把发布前内容质量检查前移到用户操作流程中。本 Phase 仍坚持默认 mock、Desktop-first、普通视图优先与无审核步骤。

### Round 47 - 轻量 UI 细节修正

- 目标：修掉当前 UI 中“看起来奇怪但不涉及业务模型”的细节。
- 范围：左上角 logo 从“发”字方块改成更轻的色块/圆点或仅文字品牌；顶部品牌区压低视觉权重；作品列表行距、缩略图占位、按钮密度再微调。
- 非目标：再次大改页面架构、改变上传/排期/预览 API。
- 输入：当前 Notion / Linear 风 `admin_template.html`、Playwright 截图、用户截图反馈。
- 输出：更克制的顶部品牌与作品列表细节。
- 验收标准：截图中左上角不突兀，整体仍保持 Notion / Linear 风；普通视图不出现审核或内部字段。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_app.py tests/test_web_ordinary_copy.py -q` 与 Playwright 截图。
- 退出标准：仅视觉细节变更，无业务行为回归。
- 风险：过度弱化品牌导致入口识别度下降。
- 回滚点：回退至 Round 45/Notion 风模板。
- 交付项：
  - [x] 左上角品牌/标识修正
  - [x] 作品列表密度微调
  - [x] 缩略图占位弱化
  - [x] 按钮视觉层级校准
  - [x] 截图基线更新

### Round 48 - 微信草稿正文规范化与标题去重

- 目标：保证公众号草稿标题只出现在微信标题栏，正文里不再重复文章标题。
- 范围：引入 `display_body` / `publish_body` 概念；Markdown 首个同名 H1 在发布正文中移除；frontmatter `title` 与正文首行同名 H1 时移除；HTML 首个同名 `<h1>` 可在发布正文中移除；更新 mock/real adapter 测试。
- 非目标：富文本编辑器、完整微信公众号样式还原。
- 输入：`parser.py`、`renderers/markdown.py`、`adapters/real.py`、已有 parser/renderer/real adapter 测试。
- 输出：草稿标题与正文边界清晰的发布正文。
- 验收标准：真实草稿 payload 中 `articles[0].title` 是标题，`articles[0].content` 不含重复首标题。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_parser.py tests/test_renderer_markdown.py tests/test_real_adapter.py -q`。
- 退出标准：标题提取、摘要生成和正文渲染行为有明确测试覆盖。
- 风险：历史文章依赖正文标题作为视觉标题。
- 回滚点：仅在 publish 渲染层去重，不修改原始 `articles.body`。
- 交付项：
  - [x] 发布正文规范化函数
  - [x] Markdown 同名首标题去重
  - [x] HTML 同名首标题去重
  - [x] real draft payload 测试
  - [x] mock/preview 行为回归测试

### Round 49 - 公众号效果预览修正

- 目标：预览弹窗展示“接近公众号正文”的最终渲染效果，而不是 HTML 源码。
- 范围：新增统一 `build_publish_preview(article)` 或同等函数；Web 预览和 real draft 共用同一套渲染入口；对已转义 HTML / 字符实体内容做合理归一化；预览弹窗增加“公众号正文预览”语义与近似微信正文样式；高级信息保留原始 HTML/Markdown。
- 非目标：像素级复刻公众号编辑器。
- 输入：`/api/articles/{id}/render-preview`、`renderers/markdown.py`、真实 draft 渲染路径、图二反馈场景。
- 输出：同源渲染的 Web 预览和发布正文。
- 验收标准：图二场景中弹窗显示可读正文，不显示 HTML 标签源码；与真实 draft content 使用同源渲染。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_publish_preview.py tests/test_web_app.py -q`。
- 退出标准：用户看到的预览足以判断发布正文大致效果。
- 风险：过度归一化可能破坏合法 HTML。
- 回滚点：保留原始内容在高级信息区，仅普通预览使用归一化结果。
- 交付项：
  - [x] 统一发布预览构建函数
  - [x] Web render-preview 接入同源渲染
  - [x] 预览弹窗微信近似样式
  - [x] 转义 HTML 归一化测试
  - [x] 高级区保留原始内容

### Round 50 - 作品回收站与可逆删除

- 目标：用户可以从页面删除已收录作品，先进入回收站，不立刻物理删除。
- 范围：数据模型新增软删除字段（如 `articles.deleted_at` / `delete_status`）；Web 作品列表增加“删除”；普通作品库隐藏已删除作品；新增回收站视图；可恢复；删除时取消或隐藏该作品未完成任务。
- 非目标：彻底删除文件和数据库记录（见 Round 51）。
- 输入：articles/publish_jobs/wechat_drafts/events 数据模型、当前作品库 UI。
- 输出：可逆删除与回收站入口。
- 验收标准：页面删除后作品不再出现在作品库/发布队列，可在回收站恢复。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_trash.py -q`。
- 退出标准：软删除不影响未删除作品的 scan/plan/run-once。
- 风险：软删除状态与任务状态不一致。
- 回滚点：隐藏回收站入口并保留数据库字段。
- 交付项：
  - [x] 软删除迁移
  - [x] 删除 API
  - [x] 恢复 API
  - [x] 回收站视图
  - [x] 任务隐藏/取消策略测试

### Round 51 - 清空回收站与彻底删除

- 目标：用户清空回收站后，数据库和本地项目里的相关内容都删除干净。
- 范围：删除 articles 记录、关联 publish_jobs、wechat_drafts、events 中可安全删除/脱钩的数据；删除文章源文件和封面文件；避免误删非本项目目录文件；已发布内容仅删除本地记录和本地文件，不撤回公众号内容；清空前二次确认。
- 非目标：调用微信撤回/删除已发布内容。
- 输入：Round 50 回收站状态、文件路径安全校验、SQLite 外键关系。
- 输出：不可恢复的清空回收站能力。
- 验收标准：清空后数据库无该文章及未完成任务，相关本地文件不存在；不会删除项目外路径。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_trash.py tests/test_migrations.py -q`。
- 退出标准：删除影响范围可解释，危险操作有二次确认。
- 风险：误删用户文件或保留孤儿记录。
- 回滚点：仅暴露逐条彻底删除，不提供一键清空。
- 交付项：
  - [x] 清空回收站 API
  - [x] 文件路径安全校验
  - [x] 关联数据删除/脱钩策略
  - [x] 二次确认文案
  - [x] 彻底删除测试

### Round 52 - 批量管理与删除一致性

- 目标：让“用户可操作的内容都可以删除”，并保证批量操作不混乱。
- 范围：作品库多选；批量删除/恢复；发布队列取消待发布任务；上传临时文件/孤儿封面清理策略；高级信息中提供删除影响预览。
- 非目标：复杂权限、多用户审批。
- 输入：Round 50/51 删除能力、作品库和发布队列 UI。
- 输出：批量管理与一致的删除/恢复路径。
- 验收标准：作品、封面、未完成任务、回收站项都有清晰删除/恢复路径。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_trash.py tests/test_ui_e2e.py -q`。
- 退出标准：批量操作不会影响未选中作品。
- 风险：批量操作误选/误删。
- 回滚点：保留单条删除/恢复，隐藏批量入口。
- 交付项：
  - [x] 多选 UI
  - [x] 批量删除/恢复 API
  - [x] 待发布任务取消 API
  - [x] 孤儿封面清理策略
  - [x] 删除影响预览

### Round 53 - 发布前内容质量检查

- 目标：把“标题重复、封面缺失、摘要过长、正文疑似 HTML 源码”等问题在发布前提前发现。
- 范围：预检清单新增标题重复、正文首段异常、正文为空、疑似转义 HTML；作品卡片显示轻量提示；执行到点发布前阻断严重问题，提示用户先预览/修复。
- 非目标：自动改写文章内容。
- 输入：Round 48/49 的规范化渲染、现有 publish preflight。
- 输出：发布前内容质量检查与可读提示。
- 验收标准：HTML 源码预览问题能在发布前被检测或被规范化；严重问题不进入真实发布。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_content_quality.py tests/test_web_round39_plus.py tests/test_publish_preview.py -q`。
- 退出标准：预检提示不打扰 mock 演练，但真实发布路径有明确阻断。
- 风险：误报过多影响正常发布。
- 回滚点：仅提示不阻断，保留高级区详情。
- 交付项：
  - [x] 内容质量检查器
  - [x] 预检清单接入
  - [x] 作品卡片轻量提示
  - [x] 真实发布阻断策略
  - [x] 质量检查测试

### Round 54 - 真实微信 API 闭环验证

- 目标：用仓库已配置的真实微信凭证，批量验证 token、封面上传、草稿创建，并保存可审计报告。
- 范围：`scripts/real_api_check.py`；`fixtures/real_api_samples/` 样本；`reports/real_api_runs/` 报告；README 说明；工作台帮助文案与 `real + 草稿-only` 配置对齐。
- 非目标：默认开启 `freepublish/submit`；无限制烧 API；提交 `.env`。
- 输入：Round 53 内容质量检查、RealWechatAdapter、本地 `.env`。
- 输出：可重复执行的真实 API 验证入口与每轮报告。
- 验收标准：`real_api_check` 在 `WECHAT_MODE=real` 下完成至少 3 条草稿样本且报告落盘；gate 冒烟通过。
- 建议测试/冒烟命令：`python3 scripts/real_api_check.py --samples 3`；`python3 scripts/agent_gate.py gate`。
- 退出标准：失败时报告含可读错误且不泄露 secret；`WECHAT_ENABLE_PUBLISH=true` 时不自动提交发布。
- 风险：误创建过多公众号草稿。
- 回滚点：仅保留 token 探测，跳过 `draft/add`。
- 交付项：
  - [x] real_api_check 脚本
  - [x] 样本 fixtures
  - [x] 报告目录与示例
  - [x] README / 帮助文案
  - [x] agent_gate round_054 冒烟

### Round 55 - Auto-Approved Real API Pipeline

- 目标：真实微信 API 生成草稿后默认自动通过（无人工审核等待），并继续 scan/run-once 下游，报告可审计。
- 范围：`scripts/auto_approve_pipeline.py`；`real_api_check` 的 auto_approve 元数据；`reports/auto_approve_pipeline/`；环境变量 `AUTO_APPROVE_GENERATIONS` / `REVIEW_MODE`。
- 非目标：移除人工发布确认护栏（`WECHAT_ENABLE_PUBLISH=true` 时 UI 仍须确认）；默认自动 freepublish/submit。
- 输入：Round 54 real_api_check、本地 `.env`（`WECHAT_MODE=real` + 草稿-only）。
- 输出：每轮 pipeline 报告（JSON + Markdown）；样本带 `review_status=auto_approved` 元数据。
- 验收标准：`auto_approve_pipeline --round N` 在 real 模式下完成 ≥3 条草稿样本；gate 冒烟通过；不泄露 secret。
- 建议测试/冒烟命令：`python3 scripts/auto_approve_pipeline.py --round 1 --samples 3`；`python3 scripts/agent_gate.py gate`。
- 退出标准：失败时报告含可读错误；切回人工模式：`REVIEW_MODE=manual` 且 `AUTO_APPROVE_GENERATIONS=false`。
- 风险：误创建过多公众号草稿；与历史「审核」概念混淆（本仓库 Round 43 已移除审核，此处仅指 pipeline 元数据）。
- 回滚点：仅保留 `real_api_check`，禁用 `auto_approve_pipeline`。
- 交付项：
  - [x] auto_approve_pipeline 脚本
  - [x] real_api_check auto_approve 元数据
  - [x] reports/auto_approve_pipeline 报告
  - [x] README / .env.example 说明
  - [x] agent_gate round_055 冒烟


### Round 56 - 路线收敛治理轮

- 目标：把项目从“多平台发布器幻想版”收敛回“个人本地微信公众号发布工作台 MVP”，明确阶段一只优先打通微信公众号闭环，并把其他平台全部降级为后期 backlog。
- 范围：路线发散审计、产品愿景、微信公众号优先架构、收敛路线图、平台优先级、repo protocol、安全默认值、README、backlog 归档与 browser_assist 重新定位。
- 非目标：实现知乎、豆瓣、小红书、视频号、Bilibili、抖音、快手、网易云音乐；实现完整多平台 adapter；重构数据库；引入大型前端框架或队列系统；默认真实发布。
- 输入：当前仓库实现、真实微信 API 验证结果、参考仓吸收文档、现有治理文件、已暴露的摘要/排版/封面/Web/scheduler 卡点。
- 输出：`docs/route_convergence_audit.md`、`docs/product_vision.md`、`docs/architecture.md`、`docs/roadmap_converged.md`、`docs/platform_priority.md`、`docs/wechat_browser_assist_strategy.md`、`docs/backlog/`、同步后的协议、README 与安全默认值。
- 验收标准：项目 P0 已明确为微信公众号闭环；其他平台均进入后期 backlog；`scan/plan/run-once` 和微信草稿链路不回归；默认 mock 不联网，real 模式用于真实 API 测试；browser_assist 被定义为个人自用后备方案且不绕过平台风控；治理测试和基础 smoke 通过。
- 建议测试/冒烟命令：`npm run check:mcp && python3 scripts/check_rounds_doc.py && python3 -m pytest tests/test_agent_gate.py tests/test_check_rounds_doc.py tests/test_publish_config.py -q && python3 -m pytest tests/test_parser.py tests/test_digest_limits.py tests/test_scheduler_hardening.py tests/test_real_adapter.py tests/test_workflow.py -q`。
- 退出标准：后续 Agent 读 README、product_vision、architecture、roadmap_converged、platform_priority 和 repo_protocol 后，不会把多平台扩展当成当前任务。
- 风险：旧长期蓝图继续误导推进方向；过度收敛时误删未来设计材料；安全默认值与文档不一致。
- 回滚点：保留当前微信 CLI 与 adapter；backlog 文档可从 `docs/backlog/` 重新引用；安全默认值可通过显式环境变量开启。
- 交付项：
  - [x] 路线发散审计
  - [x] 产品愿景收敛
  - [x] 微信公众号优先架构
  - [x] roadmap_converged.md
  - [x] platform_priority.md
  - [x] wechat_browser_assist_strategy.md
  - [x] 多平台文档归档到 backlog
  - [x] repo_protocol / rounds / agent_gate / tests 同步
  - [x] mock 默认不联网与 real API 测试模式验证
  - [x] 治理测试和 CLI smoke 记录

### Round 57 - 收敛后微信链路稳定化（启动）

- 目标：按 `docs/roadmap_converged.md` Phase 1 Round 2，巩固 `scan → plan → run-once → create_draft` mock 主链路。
- 范围：聚焦测试与小修复；梳理 CLI/adapter 差异；不扩展多平台。
- 非目标：多平台 adapter、数据库大迁移、真实发布默认开启。
- 输入：Round 56 收敛文档、现有 `tests/test_wechat_chain_stability.py`。
- 输出：链路稳定性说明、补强测试、必要的小修复。
- 验收标准：`tests/test_wechat_chain_stability.py` 通过；mock 默认不回归；`WECHAT_ENABLE_PUBLISH=false` 时 draft-only 行为可解释。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_chain_stability.py tests/test_scheduler_hardening.py -q`。
- 退出标准：收敛路线图 Round 2 入口可被 Agent 直接执行，不回到多平台叙事。
- 风险：真实 API 测试误开 `WECHAT_ENABLE_PUBLISH`；重复草稿。
- 回滚点：仅保留文档与测试登记，暂停链路代码改动。
- 交付项：
  - [x] 收敛路线图 Round 2 入口登记（agent_gate `round_057`）
  - [x] 链路稳定性审计文档
  - [x] mock/real draft-only 行为对照测试补强

### Round 58 - 摘要错误码与草稿幂等

- 目标：降低真实草稿创建失败和重复创建风险。
- 范围：统一 digest 120 字；微信 errcode 可读映射；同 content_hash 草稿幂等复用。
- 非目标：草稿更新大功能；默认真实发布。
- 输入：Round 57 主链路、`parser.clamp_summary`、RealWechatAdapter。
- 输出：`wechat_errors.py`、`draft_idempotency.py`、`docs/wechat_digest_errors_idempotency.md`。
- 验收标准：长摘要不超限；`WechatApiError` 含 human_hint；重复执行不新增 draft 行。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_digest_limits.py tests/test_wechat_digest_errors_idempotency.py tests/test_real_adapter.py -q`。
- 退出标准：job_failed 事件不含 secret；幂等复用有 `draft_idempotent_reuse` 审计。
- 风险：内容变更但 hash 未更新时仍复用旧草稿。
- 回滚点：移除幂等查询，仅保留摘要截断与错误码说明。
- 交付项：
  - [x] 错误码说明与 human_hint
  - [x] 摘要统一与测试
  - [x] 草稿创建幂等实现与测试
  - [x] agent_gate round_058 冒烟

### Round 59 - 微信公众号 HTML 渲染器

- 目标：让本地 Markdown 稳定转换为公众号正文 HTML，预览与草稿同源。
- 范围：`renderers/wechat.py`、发布预览、规则文档与 fixture 测试。
- 非目标：复杂主题系统、多平台 renderer。
- 输入：Round 58 摘要/幂等、`publish_preview`。
- 输出：`docs/wechat_html_renderer.md`、渲染增强、测试样例。
- 验收标准：Web 预览和 `draft/add` 同源；正文不重复标题；基础样式稳定。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_renderer.py tests/test_publish_preview.py -q`。
- 退出标准：常见 Markdown 块级语法有覆盖测试；内嵌 HTML 不转义泄漏。
- 风险：生成微信不接受的标签；破坏已有 HTML 输入。
- 回滚点：仅保留旧版 `render_wechat_html` 子集。
- 交付项：
  - [x] 渲染规则文档
  - [x] wechat 渲染器增强（列表/引用/代码/粗斜体）
  - [x] 预览与 publish 同源测试
  - [x] agent_gate round_059 冒烟

### Round 60 - 公众号效果预览快照

- 目标：发布前在本地看到近似公众号正文预览，并可落盘快照供比对。
- 范围：`preview_snapshot.py`、Web 预览弹窗、`render-preview` API、CLI、存储目录与测试。
- 非目标：完整模拟公众号后台；跨平台预览。
- 输入：Round 59 同源 HTML 渲染、`publish_preview`、`content_quality` 提示。
- 输出：`docs/wechat_preview_snapshot.md`、`storage/preview_snapshots/`、预览包与快照文件。
- 验收标准：统一预览入口；显示摘要、正文、封面与阻断项；标注近似预览；可选保存 JSON/HTML。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_preview_snapshot.py tests/test_web_app.py -q -k preview`。
- 退出标准：API/CLI 快照写入成功；Web 预览展示封面与提示；pytest 通过。
- 风险：用户误以为预览与微信后台完全一致。
- 回滚点：恢复仅 `build_publish_preview` 的简单 API 响应。
- 交付项：
  - [x] 预览包与快照模块
  - [x] API/CLI 与 Web 预览增强
  - [x] 文档与 .gitignore
  - [x] agent_gate round_060 冒烟

### Round 61 - 封面资产管理

- 目标：建立微信公众号封面素材的本地扫描、绑定与孤儿清理能力。
- 范围：`cover_assets/manager.py`、封面 API/CLI、Web 扫描入口、文档与测试。
- 非目标：视频封面；多平台素材库；完整裁剪编辑器。
- 输入：既有 `covers_dir`/`cover_assets`、`articles.cover_path`、默认 thumb 配置。
- 输出：`docs/cover_asset_management.md`、扫描/绑定/修复/清理 API 与 `cover-scan` CLI。
- 验收标准：单篇封面可绑定；缺省回退默认封面；无效路径可修复；孤儿可列出并安全删除。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_cover_manager.py tests/test_cover_assets.py -q`。
- 退出标准：扫描报告准确；stem 绑定与孤儿清理有测试覆盖。
- 风险：误删仍被引用的封面；绑定错 stem。
- 回滚点：仅保留 `covers_dir` 单目录孤儿清理。
- 交付项：
  - [x] 封面资产管理模块
  - [x] API/CLI 与 Web 扫描按钮
  - [x] 多目录孤儿清理
  - [x] agent_gate round_061 冒烟

### Round 62 - 封面裁剪与双比例预览

- 目标：发布前在桌面 Web 预览横向 2.35:1 与方形 1:1 封面效果，并保存裁剪配置。
- 范围：`cover_assets/crop_preview.py`、封面 API、批量封面弹窗双预览、文档与测试。
- 非目标：复杂图片编辑器；AI 作图。
- 输入：Round 61 封面路径与 `cover_config_json`、现有裁剪编辑器。
- 输出：`docs/cover_crop_dual_preview.md`、双比例 API、Web 实时 CSS 预览（Pillow 可选 JPEG）。
- 验收标准：两种比例可预览；配置含 crop/focal 可保存；无 Pillow 时优雅降级。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_cover_crop_preview.py tests/test_web_batch_select.py -q`。
- 退出标准：pytest 通过；8080 批量封面弹窗可见双预览。
- 风险：预览与微信后台像素级不一致。
- 回滚点：仅保留 2.35:1 单视口编辑器。
- 交付项：
  - [x] 裁剪/方形推导与双预览 API
  - [x] Web 双比例 CSS 预览
  - [x] Pillow 可选 JPEG 渲染
  - [x] agent_gate round_062 冒烟

### Round 63 - 多合集内容库

- 目标：支持多个微信公众号合集/专栏的本地文章管理与扫描导入。
- 范围：`collection.yaml`、合集扫描、`collections.config_json`、Web 筛选、API、文档与测试。
- 非目标：跨项目 publish_manifest；复杂卷册编排 UI。
- 输入：既有 `collections` 表、`articles/inbox`、`scan_inbox`。
- 输出：`content/collections/`、`docs/multi_collection_library.md`、扫描与 API 增强。
- 验收标准：不同合集作品可区分；根 inbox 仍进默认合集；plan/scan 兼容旧目录。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_multi_collection.py tests/test_content_library.py -q`。
- 退出标准：YAML 合集可导入；Web 合集下拉筛选有效。
- 风险：合集 inbox 与根 inbox 重复扫描同一文件。
- 回滚点：仅扫描根 `articles/inbox`。
- 交付项：
  - [x] collection.yaml 发现与同步
  - [x] 多路径 inbox 扫描
  - [x] API/Web 合集筛选
  - [x] agent_gate round_063 冒烟

### Round 64 - 合集排期规则

- 目标：不同合集拥有可预测的发布时间规则，并与自动 plan 集成。
- 范围：`collection_schedule.py`、`plan.py`、`collection.yaml` schedule 块、Web 文案、文档与测试。
- 非目标：复杂日历 UI；跨平台排期。
- 输入：Round 63 多合集模型、全局 `config/rules.yaml` schedule。
- 输出：`docs/collection_schedule_rules.md`、按合集 `by_collection`/`hints`、demo 合集 schedule 示例。
- 验收标准：同合集与跨合集排期可预测；不重复生成 pending；冲突有可读 hints。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_collection_schedule.py tests/test_web_schedule.py -q`。
- 退出标准：pytest 通过；plan API 返回合集级摘要。
- 风险：合集规则与全局规则叠加导致窗口内排不下。
- 回滚点：仅使用全局 schedule，忽略 collection.yaml schedule。
- 交付项：
  - [x] 合集 schedule 解析与 plan 分组
  - [x] stagger / window_days / 每日上限
  - [x] humanize_plan_result hints
  - [x] agent_gate round_064 冒烟

### Round 65 - Web 控制台 MVP

- 目标：桌面优先本地工作台 MVP：概览、导航、scan/plan/run 入口、发布队列与下一步提示。
- 范围：admin_template、overview/workbench API、user_copy、Web 测试与文档。
- 非目标：React/Vue 重写；裸露数据库路径于普通视图。
- 输入：Round 19–37 普通用户视图与 Round 64 合集能力。
- 输出：`workbench_mvp`、扫描收件箱按钮、队列状态筛选、`docs/web_console_mvp_converged.md`。
- 验收标准：Web 可完成导入（上传/扫描）、排期、执行并查看队列与操作记录；高级信息默认关闭。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_web_console_mvp.py tests/test_web_app.py -q`。
- 退出标准：8080 mock 浏览器验证核心 API 无失败；pytest 通过。
- 风险：队列筛选与 overview 数据不一致。
- 回滚点：队列仍用 overview.recent_jobs。
- 交付项：
  - [x] 下一步提示与 scan 入口
  - [x] /api/jobs 状态筛选与队列 Tab
  - [x] agent_gate round_065 冒烟

### Round 66 - 文章详情与预览页面

- 目标：单篇发布前状态可检查，下一步动作明确。
- 范围：`/articles/{id}`、`/api/articles/{id}`、详情模板、预检与预览集成。
- 非目标：多平台 payload 页。
- 输入：render-preview、publish_preflight 逻辑、作品库卡片。
- 输出：`docs/article_detail_preview.md`、详情页与 API、工作台「详情」入口。
- 验收标准：长摘要/缺封面/渲染问题可见；mock 草稿不误认为真实创建。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_article_detail_page.py tests/test_web_app.py -q`。
- 退出标准：8080 详情与预览 API 无失败；pytest 通过。
- 风险：详情与弹窗预览数据不一致。
- 回滚点：仅保留弹窗预览。
- 交付项：
  - [x] 详情路由与 API
  - [x] 预检与下一步提示
  - [x] agent_gate round_066 冒烟

### Round 67 - 发布队列页面

- 目标：pending/running/failed/done 队列表格可读，失败可重试。
- 范围：`queue_display`、jobs API 增强、重试 API、Web 队列区、测试与文档。
- 非目标：分布式队列；跨平台队列。
- 输入：Round 65 队列 Tab、events.job_failed、workflow.retry。
- 输出：`docs/publish_queue_page.md`、失败原因列、重试入口。
- 验收标准：用户能看懂到点/失败任务并执行重试或取消。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_publish_queue_page.py -q`。
- 退出标准：8080 队列 Tab API 无失败；pytest 通过。
- 风险：失败原因依赖事件表完整性。
- 回滚点：队列仅显示标题与时间。
- 交付项：
  - [x] 失败原因与已到点标记
  - [x] retry / bulk-retry API
  - [x] agent_gate round_067 冒烟

### Round 68 - 微信草稿管理页面

- 目标：展示 `wechat_drafts` 记录，关联作品，mock 下不误导为公众号后台全量草稿。
- 范围：`drafts_display`、drafts API、工作台 `#drafts`、`/drafts`、测试与文档。
- 非目标：读取公众号后台全部草稿；暴露完整敏感 payload。
- 输入：Round 67 队列页、scheduler 写入 `wechat_drafts`。
- 输出：`docs/publish_drafts_page.md`、列表/筛选/摘要 API。
- 验收标准：用户能看懂哪些作品已有本地微信草稿记录；8080 mock 浏览器无 API 失败。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_drafts_page.py -q`。
- 退出标准：gate round_068 通过。
- 风险：media_id 被误解为公开链接。
- 回滚点：仅保留作品详情中的草稿提示。
- 交付项：
  - [x] drafts API 与列表展示
  - [x] mock 演练说明
  - [x] agent_gate round_068 冒烟

### Round 69 - 本地 scheduler 稳定化

- 目标：run-once 更可靠：claim、锁、退避重试、卡住恢复、健康检查。
- 范围：`scheduler/claim.py`、`scheduler/health.py`、`runtime`/`domain`、迁移、CLI、测试与文档。
- 非目标：Redis/Celery；`schedule_state` 分列。
- 输入：Round 68 草稿页、既有 `run_due_jobs`。
- 输出：`docs/scheduler_stability.md`、`scheduler-health` 命令。
- 验收标准：到期任务可 claim；失败可退避；running 不卡死；pytest 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_scheduler_stability.py tests/test_scheduler_hardening.py -q`。
- 退出标准：gate round_069 通过；`scheduler-health` 可输出队列摘要。
- 风险：锁 TTL 过短导致并发 run-once；退避期间重复手动重试。
- 回滚点：移除 claim 列与锁表，恢复简单 pending→running 更新。
- 交付项：
  - [x] claim / lock / stale recovery / backoff
  - [x] scheduler-health
  - [x] agent_gate round_069 冒烟

### Round 70 - Scheduler 常驻运行文档

- 目标：用户能按文档在本机长期启动/停止 scheduler（mock 默认可演练）。
- 范围：`docs/scheduler_runbook.md`、`deploy/examples/scheduler/`、包装脚本、`scheduler-daemon` CLI、README/用户手册。
- 非目标：云部署安装器；复杂守护进程框架。
- 输入：Round 69 稳定化（claim/锁/health）。
- 输出：launchd/systemd/cron 示例、tmux 与故障处理说明。
- 验收标准：示例文件齐全；手册区分 mock/real/草稿-only；pytest 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_scheduler_runbook.py -q`。
- 退出标准：gate round_070 通过。
- 风险：用户同时开 scheduler 与 cron 导致锁冲突（文档已强调二选一）。
- 回滚点：仅保留 CLI `scheduler` 单行说明。
- 交付项：
  - [x] scheduler_runbook 与 deploy 示例
  - [x] run_scheduler_daemon.sh / cron_run_once.sh
  - [x] agent_gate round_070 冒烟

### Round 71 - 微信草稿更新能力

- 目标：在可行范围内更新已创建微信草稿（draft/update），不可更新时有替代说明。
- 范围：`draft_update.py`、适配器 `update_draft`、CLI/Web API、指纹幂等、测试与文档。
- 非目标：默认 browser_assist 改稿；覆盖错误 media_id。
- 输入：Round 68 草稿列表、Round 69 稳定化执行链路。
- 输出：`docs/draft_update.md`、能力矩阵更新。
- 验收标准：mock 可更新本地记录；real 调 draft/update；未改内容跳过；旧草稿 superseded。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_draft_update.py -q`。
- 退出标准：gate round_071 通过；详情页可触发更新 API。
- 风险：微信 API 字段变更；无草稿时误点更新。
- 回滚点：移除 update-draft API，仅保留创建草稿。
- 交付项：
  - [x] update_draft mock/real
  - [x] CLI update-draft 与 Web 按钮
  - [x] agent_gate round_071 冒烟

### Round 72 - 微信字段能力矩阵核验

- 目标：梳理公众号字段的 API 支持、本仓库实现、缺口与处理方式。
- 范围：`wechat_field_matrix.py`、`wechat_capability_matrix.md`、API/CLI、测试。
- 非目标：其他平台矩阵；未核验字段不得标为 supported。
- 输入：Round 71 草稿更新、现有 adapter 字段。
- 输出：字段缺口摘要、debug 页矩阵 JSON。
- 验收标准：每字段有四列说明；待核验项明确标注。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_field_matrix.py -q`。
- 退出标准：gate round_072 通过；`/debug` 可加载 `/api/wechat-field-matrix`。
- 风险：误报 API 能力导致用户过度依赖自动化。
- 回滚点：仅保留原高层能力表。
- 交付项：
  - [x] 字段矩阵代码与文档
  - [x] field-matrix CLI 与 Web API
  - [x] agent_gate round_072 冒烟

### Round 73 - browser_assist 后备流程

- 目标：为微信 API 缺口定义本地 browser_assist 干跑流程（人机确认）。
- 范围：`adapters/browser_assist/workflow.py`、`browser_assist_runbook.md`、CLI/Web API、测试。
- 非目标：完整 Playwright 自动发文；保存 cookie/密码。
- 输入：Round 72 字段矩阵缺口。
- 输出：操作清单、checkpoint、guardrails、dry-run JSON。
- 验收标准：计划状态为 `awaiting_human_confirmation`；禁止项在 guardrails 中可查。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_browser_assist_workflow.py -q`。
- 退出标准：gate round_073 通过；`/debug` 可加载 `/api/browser-assist-plan`。
- 风险：误用为自动发布工具。
- 回滚点：仅保留策略文档，移除 API。
- 交付项：
  - [x] workflow 干跑骨架与 runbook
  - [x] browser-assist-plan CLI 与 Web API
  - [x] agent_gate round_073 冒烟

### Round 74 - 人工确认与 proof 记录

- 目标：记录人工确认与最终发布证明；无 proof 不标记正式发布。
- 范围：`publish_proofs` 迁移、`review/proof.py`、Web/CLI/API、作品详情表单、文档。
- 非目标：恢复内容审核门禁；无人值守发布。
- 输入：Round 73 browser_assist 干跑计划。
- 输出：`proof_of_publish.md`、`waiting_confirmation` 状态与 proof 表。
- 验收标准：待确认任务需 proof 才 `done`+`published`；API/详情页可提交。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_publish_proof.py -q`。
- 退出标准：gate round_074 通过；`/debug` 可加载 `/api/waiting-confirmation`。
- 交付项：
  - [x] proof 模块与迁移
  - [x] Web/CLI 入口
  - [x] agent_gate round_074 冒烟

### Round 75 - 可选正式发布策略

- 目标：`WECHAT_MODE=real` 下可选正式发布；全局/任务级 draft-only 可区分。
- 范围：`publish_policy.py`、`optional_real_publish.md`、预检/UI 徽章、`publish_skipped_draft_only` 事件。
- 非目标：无人值守默认正式发布；绕过二次确认。
- 输入：Round 74 proof 记录、现有 `publish_config`。
- 输出：策略 API、工作台安全条与队列徽章。
- 验收标准：mock 不联网；`WECHAT_ENABLE_PUBLISH=false` 不 freepublish；任务「仅草稿」不提交发布。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_optional_real_publish.py tests/test_publish_config.py -q`。
- 退出标准：gate round_075 通过；`/api/status` 含 `publish_policy`。
- 风险：误开 `WECHAT_ENABLE_PUBLISH` 导致意外发布。
- 回滚点：移除 publish_policy，保留原有 should_submit_publish。
- 交付项：
  - [x] publish_policy 与 status/preflight API
  - [x] 队列/详情有效行为徽章
  - [x] agent_gate round_075 冒烟

### Round 76 - 微信公众号闭环验收

- 目标：阶段一 MVP 闭环验收清单与回归入口。
- 范围：`wechat_mvp_acceptance.md`、`test_wechat_mvp_acceptance.py`。
- 非目标：启动 Phase 2 多平台开发。
- 输入：Round 0–75 交付物。
- 输出：验收文档与回归命令清单。
- 验收标准：文档含闭环步骤；核心模块可导入；chain_stability 冒烟通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_mvp_acceptance.py tests/test_wechat_chain_stability.py -q`。
- 退出标准：gate round_076 通过。
- 风险：验收清单与实现漂移。
- 回滚点：仅保留文档，不阻塞后续修复轮。
- 交付项：
  - [x] MVP 验收文档
  - [x] agent_gate round_076 冒烟

### Round 77 - manual_export 通用 outbox

- 目标：为文本平台扩展提供低风险 manual_export 导出包。
- 范围：`adapters/manual_export/outbox.py`、CLI/Web API、作品详情按钮、`manual_export_runbook.md`。
- 非目标：联网登录第三方平台；自动标记已发布。
- 输入：Phase 1 作品库与预览渲染。
- 输出：`outbox/` 目录下的 md/html/manifest/说明。
- 验收标准：导出后文章状态不变；含 proof_required 提示。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_manual_export.py -q`。
- 退出标准：gate round_077 通过；详情页可导出。
- 风险：用户误以为导出等于发布。
- 回滚点：移除 export API，保留微信主线。
- 交付项：
  - [x] outbox 导出实现
  - [x] CLI export-outbox 与 Web API
  - [x] agent_gate round_077 冒烟

### Round 78 - Phase 2 平台提示包

- 目标：启动 Phase 2 文本平台扩展；知乎/豆瓣 copy 提示与 outbox 索引。
- 范围：`phase2_text_platforms.md`、`--platform zhihu|douban`、`/api/outbox-packages`。
- 非目标：知乎/豆瓣 browser_assist 实现。
- 输入：Round 77 outbox 骨架。
- 输出：平台提示 md、`/debug` outbox 列表。
- 验收标准：`zhihu_copy.md` 随 platform=zhihu 生成；Phase 2 文档可读。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_manual_export_platform.py -q`。
- 退出标准：gate round_078 通过。
- 风险：范围蔓延到多平台 adapter。
- 回滚点：仅保留 generic 导出。
- 交付项：
  - [x] 平台提示包与 Phase 2 说明
  - [x] outbox 列表 API
  - [x] agent_gate round_078 冒烟

### Round 79 - 知乎发布包模板

- 目标：生成知乎可人工复制的完整发布包（标题/导语/正文/封面/清单）。
- 范围：`platforms/zhihu.py`、`zhihu_publish_pack.md`、Web 知乎导出按钮。
- 非目标：登录知乎或自动发布。
- 输入：Round 77–78 outbox 骨架。
- 输出：`zhihu_*` 字段文件与 `zhihu_publish.md`。
- 验收标准：只导出；manifest.platform=zhihu；文章状态不变。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_zhihu_publish_pack.py -q`。
- 退出标准：gate round_079 通过；详情页可导出知乎包。
- 风险：误称已对接知乎 API。
- 回滚点：回退为 zhihu_copy.md 简版。
- 交付项：
  - [x] 知乎发布包文件集
  - [x] /api/manual-export/platforms
  - [x] agent_gate round_079 冒烟

### Round 80 - 豆瓣发布包模板

- 目标：生成豆瓣可人工复制的发布包（标题/正文/标签提示/封面）。
- 范围：`platforms/douban.py`、详情页豆瓣导出。
- 非目标：登录豆瓣；自动发布。
- 输入：Round 79 平台包结构。
- 输出：`douban_*` 文件集。
- 验收标准：platform=douban 导出完整；不联网。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_douban_publish_pack.py -q`。
- 退出标准：gate round_080 通过。
- 风险：范围蔓延到 browser_assist。
- 回滚点：仅保留知乎包。
- 交付项：
  - [x] 豆瓣发布包文件集
  - [x] agent_gate round_080 冒烟

### Round 81 - 知乎 browser_assist 评估

- 目标：评估知乎是否适合本地 browser_assist（dry-run，不真发）。
- 范围：`zhihu_workflow.py`、`zhihu_browser_assist.md`、CLI/Web `--platform zhihu`。
- 非目标：登录知乎、自动填表、自动发布。
- 输入：Round 79 知乎发布包。
- 输出：评估结论、checkpoints、guardrails、步骤清单。
- 验收标准：计划含 assessment；不绕过验证码。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_zhihu_browser_assist.py -q`。
- 退出标准：gate round_081；`/debug` 可见知乎评估 JSON。
- 风险：误实现为自动发布工具。
- 回滚点：移除 zhihu platform 分支。
- 交付项：
  - [x] 知乎 dry-run 计划
  - [x] /debug 与 API 入口
  - [x] agent_gate round_081 冒烟

### Round 82 - browser_assist 多平台入口

- 目标：微信主线 browser_assist API 与多平台列表兼容。
- 范围：`plans.py`、`/api/browser-assist/platforms`、测试与 README。
- 非目标：豆瓣 browser_assist 实现。
- 输入：Round 81 多平台 plans 入口。
- 输出：平台列表 API；微信默认 plan 回归通过。
- 验收标准：`test_browser_assist_workflow` 仍通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_browser_assist_platforms.py tests/test_browser_assist_workflow.py -q`。
- 退出标准：gate round_082 通过。
- 风险：破坏微信 browser_assist 默认行为。
- 回滚点：恢复单一 workflow 导出。
- 交付项：
  - [x] browser-assist/platforms API
  - [x] agent_gate round_082 冒烟

### Round 83 - 豆瓣 browser_assist 评估

- 目标：豆瓣 browser_assist dry-run 评估（不真发）。
- 范围：`douban_workflow.py`、`douban_browser_assist.md`、debug/API/CLI。
- 非目标：登录豆瓣、自动发布。
- 输入：Round 80 豆瓣发布包。
- 输出：assessment、checkpoints、步骤。
- 验收标准：platform=douban 计划可生成；不绕过验证码。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_douban_browser_assist.py -q`。
- 退出标准：gate round_083；`/debug` 可见豆瓣评估 JSON。
- 风险：误用为自动发帖工具。
- 回滚点：移除 douban 分支。
- 交付项：
  - [x] 豆瓣 dry-run 计划
  - [x] debug/API 入口
  - [x] agent_gate round_083 冒烟

### Round 84 - Phase2 browser_assist 收口

- 目标：微信/知乎/豆瓣 browser_assist 评估入口一致可查。
- 范围：`phase2_text_platforms.md`、`test_phase2_browser_assist_index.py`。
- 非目标：新平台 adapter。
- 输入：round_081–083。
- 输出：三平台 platforms API 测试通过。
- 验收标准：wechat/zhihu/douban 均可 build_dry_run_plan。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_phase2_browser_assist_index.py -q`。
- 退出标准：gate round_084 通过。
- 风险：无。
- 回滚点：N/A。
- 交付项：
  - [x] Phase2 文档与索引测试
  - [x] agent_gate round_084 冒烟

### Round 85 - Adapter Registry 能力声明

- 目标：按 backlog adapter_design 落地非侵入式能力声明表。
- 范围：`adapters/registry.py`、`docs/adapter_registry.md`、CLI/Web API。
- 非目标：替换 `get_adapter` 运行时；注册真实 adapter 类。
- 输入：Phase2 文本平台与微信主线能力矩阵。
- 输出：`BUILTIN_CAPABILITIES`；`GET /api/adapter-registry`。
- 验收标准：含 wechat_mp/zhihu/douban；不保存 secret。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_adapter_registry.py -q`。
- 退出标准：gate round_085；`/debug` 可见 registry JSON。
- 风险：误宣称平台已可自动发布。
- 回滚点：移除 API 区块。
- 交付项：
  - [x] registry 能力与测试
  - [x] agent_gate round_085 冒烟

### Round 86 - publish_manifest 校验

- 目标：校验 `publish_manifest.json` 最小 schema（不写库）。
- 范围：`core/manifest_loader.py`、`manifests/examples/`、CLI `manifest-validate`。
- 非目标：manifest 导入 SQLite；替换 scan/plan。
- 输入：`docs/backlog/multi_project_manifest_design.md`。
- 输出：`validate_manifest` 与示例文件。
- 验收标准：示例 manifest 通过；空 targets 失败。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_manifest_validate.py -q`。
- 退出标准：gate round_086 通过。
- 风险：schema 与 backlog 漂移。
- 回滚点：仅保留 load_manifest。
- 交付项：
  - [x] 校验器与示例
  - [x] agent_gate round_086 冒烟

### Round 87 - manifest 干跑 content_package

- 目标：从 manifest 生成 content_package / payload 草稿与 registry 对照。
- 范围：`content_packages/from_manifest.py`、`manifest-dry-run` CLI、`/api/manifest/sample-dry-run`。
- 非目标：DB 迁移；跨项目日历。
- 输入：round_085 registry、round_086 校验。
- 输出：干跑 summary 含 `registry_checks`。
- 验收标准：示例 manifest 两 target 均 registered；dry-run note 明示不写库。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_manifest_dry_run.py -q`。
- 退出标准：gate round_087；`/debug` 可见 manifest 干跑 JSON。
- 风险：用户误以为已导入文章。
- 回滚点：移除 from_manifest。
- 交付项：
  - [x] 干跑与 API
  - [x] agent_gate round_087 冒烟

### Round 88 - 个人博客 local_blog 评估

- 目标：路线图 Round 28 — 评估静态站/WordPress/本地目录（dry-run，不真发）。
- 范围：`local_blog/eval_workflow.py`、`local_blog_adapter_assessment.md`、registry、CLI/API、`/debug`。
- 非目标：真实写文件；WordPress REST 联网；替代微信 scan/plan。
- 输入：round_085 adapter registry、Phase2 文本平台经验。
- 输出：三目的地 assessment；`GET /api/local-blog-plan`。
- 验收标准：static_site 推荐；wordpress 有条件；guardrails 含凭证不入库。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_local_blog_eval.py -q`。
- 退出标准：gate round_088；`/debug` 可见 static_site 与 wordpress JSON。
- 风险：误实现为自动建站。
- 回滚点：移除 local-blog API。
- 交付项：
  - [x] local_blog 干跑与测试
  - [x] agent_gate round_088 冒烟

### Round 89 - Webhook 适配器评估

- 目标：评估通知类 webhook（dry-run，不发起 HTTP）。
- 范围：`webhook/eval_workflow.py`、`webhook_adapter_assessment.md`、CLI/API、`/debug`。
- 非目标：真实 POST；将 webhook 当作发布 proof。
- 输入：round_088 local_blog 评估模式。
- 输出：generic/feishu/slack 渠道干跑；registry notification+webhook。
- 验收标准：terminal_policy 明示 webhook≠published；`WEBHOOK_URL` 仅环境变量。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_webhook_eval.py -q`。
- 退出标准：gate round_089；`/debug` 可见 webhook JSON。
- 风险：泄露 URL 到日志。
- 回滚点：移除 webhook-plan。
- 交付项：
  - [x] webhook 干跑与测试
  - [x] agent_gate round_089 冒烟

### Round 90 - Phase3 视频内容包预研

- 目标：路线图 Round 29 — 视频内容包字段与平台占位（dry-run，不上传）。
- 范围：`video_presearch.py`、`phase3_video_content_package.md`、registry 占位、video manifest 示例。
- 非目标：视频上传；改 articles 表；Bilibili 真实导出。
- 输入：content_package backlog、round_085 registry。
- 输出：bilibili/wechat_channels/xiaohongshu 预研 assessment；`video-package-plan` CLI/API。
- 验收标准：`content_type=video` manifest 校验；guardrails 含不上传。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_video_presearch.py -q`。
- 退出标准：gate round_090；`/debug` 可见视频预研 JSON。
- 风险：误实现上传 adapter。
- 回滚点：移除 video API。
- 交付项：
  - [x] 视频预研与测试
  - [x] agent_gate round_090 冒烟

### Round 91 - 微信闭环链路摘要

- 目标：工作台可读「下一步 scan/plan/run-once」建议（真实功能）。
- 范围：`wechat_chain_summary.py`、CLI、`/api/wechat-chain-summary`、overview 聚合。
- 非目标：自动执行；Phase3 开发。
- 输入：现有 SQLite 与 scan/plan 语义。
- 输出：`recommended_next_action` 与 `recommended_cli`。
- 验收标准：空库建议 scan；导入未排期建议 plan；`test_wechat_chain_stability` 仍通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_chain_summary.py tests/test_wechat_chain_stability.py -q`。
- 退出标准：gate round_091；`/debug` 可见链路摘要 JSON。
- 风险：误导用户以为已自动执行。
- 回滚点：移除 chain summary API。
- 交付项：
  - [x] 链路摘要与测试
  - [x] agent_gate round_091 冒烟

### Round 92 - Bilibili manual_export 发布包

- 目标：路线图 Round 30 — Bilibili 人工上传包骨架（不真上传）。
- 范围：`platforms/bilibili.py`、`bilibili_manual_export.md`、`export-outbox --platform bilibili`。
- 非目标：视频二进制导出；B 站 API；自动投稿。
- 输入：round_090 视频预研、manual_export 框架。
- 输出：title/description/checklist/video_placeholder 等文件。
- 验收标准：`test_bilibili_publish_pack` 通过；manifest 仍不写库视频。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_bilibili_publish_pack.py -q`。
- 退出标准：gate round_092 通过。
- 风险：用户误以为已上传。
- 回滚点：从 registry 移除 bilibili。
- 交付项：
  - [x] Bilibili 发布包
  - [x] agent_gate round_092 冒烟

### Round 93 - Bilibili browser_assist 评估

- 目标：路线图 Round 31 — 投稿页辅助评估 dry-run。
- 范围：`bilibili_workflow.py`、`browser-assist-plan --platform bilibili`、`/debug`。
- 非目标：自动上传视频；保存 cookie。
- 输入：round_092 发布包。
- 输出：assessment manual_export_first；platforms API 含 bilibili。
- 验收标准：干跑含 checkpoints；不绕过审核。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_bilibili_browser_assist.py -q`。
- 退出标准：gate round_093；`/debug` 可见 bilibili JSON。
- 风险：误作无人值守投稿工具。
- 回滚点：移除 bilibili 分支。
- 交付项：
  - [x] bilibili dry-run
  - [x] agent_gate round_093 冒烟

### Round 94 - 小红书 manual_export 发布包

- 目标：路线图 Round 32 — 小红书图文/笔记发布包预研（不真上传）。
- 范围：`platforms/xiaohongshu.py`、`xiaohongshu_manual_export.md`。
- 非目标：图集/视频二进制；自动发布；登录小红书。
- 输入：manual_export 框架、Phase3 高风控约束。
- 输出：xhs_* 文件集与发布清单。
- 验收标准：`test_xiaohongshu_publish_pack` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_xiaohongshu_publish_pack.py -q`。
- 退出标准：gate round_094。
- 风险：合规与导流违规文案。
- 回滚点：移除 xiaohongshu 平台。
- 交付项：
  - [x] 小红书发布包
  - [x] agent_gate round_094 冒烟

### Round 95 - 小红书 browser_assist 评估

- 目标：路线图 Round 33 — 小红书填表辅助评估（dry-run）。
- 范围：`xiaohongshu_workflow.py`、`/debug`、API/CLI。
- 非目标：批量灌水；保存 cookie。
- 输入：round_094 发布包。
- 输出：assessment deferred；platform xhs 别名。
- 验收标准：`browser-assist-plan?platform=xiaohongshu` 可生成。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_xiaohongshu_browser_assist.py -q`。
- 退出标准：gate round_095；`/debug` 可见小红书 JSON。
- 风险：误作自动化运营工具。
- 回滚点：移除 xhs 分支。
- 交付项：
  - [x] xhs dry-run
  - [x] agent_gate round_095 冒烟

### Round 96 - 微信视频号 manual_export

- 目标：路线图 Round 34 — 视频号人工发布包（非公众号 API）。
- 范围：`platforms/wechat_channels.py`、`wechat_channels_manual_export.md`。
- 非目标：视频上传；draft/add；与公众号状态混用。
- 输入：round_090 视频预研、manual_export。
- 输出：channels_* 文件集含公众号关系说明。
- 验收标准：`test_wechat_channels_publish_pack` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_channels_publish_pack.py -q`。
- 退出标准：gate round_096。
- 风险：用户误以为视频号=公众号已发。
- 回滚点：移除 wechat_channels 平台。
- 交付项：
  - [x] 视频号发布包
  - [x] agent_gate round_096 冒烟

### Round 97 - 微信视频号 browser_assist

- 目标：视频号助手填表辅助评估 dry-run。
- 范围：`wechat_channels_workflow.py`、`/debug`、CLI/API。
- 非目标：自动发表；代登录。
- 输入：round_096 发布包。
- 输出：manual_export_first；platform 别名 channels。
- 验收标准：terminal_policy 区分视频号与公众号 published。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_wechat_channels_browser_assist.py -q`。
- 退出标准：gate round_097。
- 风险：与 wechat_official 混淆。
- 回滚点：移除 channels 分支。
- 交付项：
  - [x] 视频号 dry-run
  - [x] agent_gate round_097 冒烟

### Round 98 - 抖音/快手 manual_export 骨架

- 目标：路线图 Round 35 — 短视频平台发布包预研（deferred，不真上传）。
- 范围：`douyin.py`、`kuaishou.py`、`short_video_douyin_kuaishou.md`。
- 非目标：登录；上传；browser_assist 自动化。
- 输入：Phase3 高风控约束。
- 输出：douyin_* / kuaishou_* 文件集。
- 验收标准：`test_douyin_kuaishou_publish_pack` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_douyin_kuaishou_publish_pack.py -q`。
- 退出标准：gate round_098。
- 风险：违规营销与自动发布。
- 回滚点：移除 douyin/kuaishou 平台。
- 交付项：
  - [x] 双平台发布包
  - [x] agent_gate round_098 冒烟

### Round 99 - 抖音/快手 deferred 评估

- 目标：统一 deferred 评估 dry-run 与 registry。
- 范围：`short_video_deferred.py`、`short-video-plan` CLI/API、`/debug`。
- 非目标：实现 adapter 上传。
- 输入：round_098 发布包。
- 输出：recommendation=deferred 双平台。
- 验收标准：`test_short_video_deferred` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_short_video_deferred.py -q`。
- 退出标准：gate round_099。
- 风险：误启动自动化运营。
- 回滚点：移除 short-video API。
- 交付项：
  - [x] deferred 评估
  - [x] agent_gate round_099 冒烟

### Round 100 - Phase4 音频/播客预研

- 目标：路线图 Round 36+ — 音频/播客 manifest 与 dry-run（不上传）。
- 范围：`audio_presearch.py`、示例 manifest、registry、`/debug`。
- 非目标：上传音频；改 articles 表；网易云真发。
- 输入：Phase3 视频预研经验、manifest 框架。
- 输出：podcast/audio/netease_music 评估；`audio-package-plan`。
- 验收标准：sample_audio/podcast manifest 校验通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_audio_presearch.py -q`。
- 退出标准：gate round_100。
- 风险：版权缺失。
- 回滚点：移除 audio API。
- 交付项：
  - [x] 音频预研与 manifest
  - [x] agent_gate round_100 冒烟

### Round 101 - 微信工作台链路提示增强

- 目标：首页「下一步」与 `wechat-chain-summary` 对齐（真实功能）。
- 范围：`workbench_mvp.py`、`admin_template.html` overview。
- 非目标：自动执行 CLI；Phase4 实现。
- 输入：round_091 链路摘要。
- 输出：`recommended_cli` 展示；空库建议 scan。
- 验收标准：`test_workbench_chain_hints` 与 MVP 测试通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_workbench_chain_hints.py tests/test_web_console_mvp.py -q`。
- 退出标准：gate round_101。
- 风险：无。
- 回滚点：恢复旧 workbench 逻辑。
- 交付项：
  - [x] 工作台增强
  - [x] agent_gate round_101 冒烟

### Round 102 - 脚本轮维护收口

- 目标：Phase0–4 与微信工作台脚本轮（0–101）收尾；全量回归与主链路 API 冒烟。
- 范围：`docs/rounds.md`、`roadmap_converged.md`、`agent_gate` 里程碑说明；`test_round_102_maintenance_smoke`。
- 非目标：Phase5 多项目实现；真上传；改 articles 表结构。
- 输入：round_101 完成态、现有 pytest 套件。
- 输出：维护轮注册表同步；scan→plan→预览→队列→草稿→/debug 关键 API 通过。
- 验收标准：全量 `pytest` + gate；维护冒烟测试通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_102_maintenance_smoke.py -q`；`python scripts/agent_gate.py gate`。
- 退出标准：gate round_102。
- 风险：无。
- 回滚点：移除 round_102 注册项。
- 交付项：
  - [x] 文档与 ROUND_ORDER 同步
  - [x] 全量 pytest + 维护冒烟
  - [x] agent_gate round_102 冒烟

### Round 103 - Phase5 多项目 manifest 干跑

- 目标：路线图 Round 39 — 在 round_086/087 上增加 `projects.yaml` 多项目编排（不写库）。
- 范围：`projects_registry.py`、`multi_project_dry_run.py`、`config/projects.example.yaml`、CLI/API、`/debug`。
- 非目标：manifest 导入 SQLite；替换 scan/plan；跨项目日历实现。
- 输入：round_086 校验、round_087 单 manifest 干跑。
- 输出：`projects-dry-run`；`/api/projects/registry` 与 `/api/projects/dry-run`。
- 验收标准：`test_multi_project_dry_run` 两项目均 ok；微信主线未改。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_multi_project_dry_run.py -q`；`python -m wechat_article_scheduler.cli projects-dry-run`。
- 退出标准：gate round_103。
- 风险：误把 manifest 当唯一导入路径。
- 回滚点：移除 projects API。
- 交付项：
  - [x] projects.yaml 示例与多项目 dry-run
  - [x] CLI/API 与 /debug
  - [x] agent_gate round_103 冒烟

### Round 104 - Phase5 跨项目发布日历预研

- 目标：路线图 Round 40 — 多项目 manifest 排期聚合、日历视图与冲突检测（不写库）。
- 范围：`cross_project_calendar.py`、CLI/API、`/debug`。
- 非目标：SaaS 日历；读取 SQLite `publish_jobs`；替代 `plan`。
- 输入：round_103 `projects.example.yaml` 与 manifest `scheduled_at`。
- 输出：`publish-calendar-dry-run`；`/api/publish-calendar/dry-run` 与 `/conflicts`。
- 验收标准：`test_cross_project_calendar` 通过；示例项目无 hard 冲突。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_cross_project_calendar.py -q`。
- 退出标准：gate round_104。
- 风险：与微信 DB 排期混淆。
- 回滚点：移除 publish-calendar API。
- 交付项：
  - [x] 日历 dry-run 与冲突检测
  - [x] CLI/API 与 /debug
  - [x] agent_gate round_104 冒烟

### Round 105 - Phase5 统一 outbox 预研

- 目标：路线图 Round 41 — 聚合各平台 `outbox/` 导出目录索引与 publish_manifest 汇总 dry-run。
- 范围：`unified_outbox_presearch.py`、`unified_outbox.example.yaml`、CLI/API、`/debug`。
- 非目标：移动/删除 outbox；标记已发布；与 `articles/` 合并。
- 输入：round_084+ `export-outbox`、round_103 projects manifest。
- 输出：`unified-outbox-dry-run`；`/api/unified-outbox/dry-run` 与 `/index`。
- 验收标准：`test_unified_outbox_presearch` 通过；只读扫描。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_unified_outbox_presearch.py -q`。
- 退出标准：gate round_105。
- 风险：误将 outbox 当发布完成。
- 回滚点：移除 unified-outbox API。
- 交付项：
  - [x] outbox 索引与 manifest 汇总
  - [x] CLI/API 与 /debug
  - [x] agent_gate round_105 冒烟

### Round 106 - Phase5 长期运维预研

- 目标：路线图 Round 42 — runbook 检查清单与健康指标 dry-run（不改生产 cron）。
- 范围：`ops_health_presearch.py`、`ops_maintenance.example.yaml`、CLI/API、`/debug`。
- 非目标：安装 launchd/cron；企业监控；破坏 SQLite。
- 输入：round_069 scheduler-health、round_070 runbook、`deploy/examples`。
- 输出：`ops-health-dry-run`；`/api/ops/health-dry-run` 与 runbook-checklist。
- 验收标准：`test_ops_health_presearch` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_ops_health_presearch.py -q`。
- 退出标准：gate round_106。
- 风险：误将 dry-run 当自动运维。
- 回滚点：移除 ops API。
- 交付项：
  - [x] runbook 清单与健康聚合
  - [x] CLI/API 与 /debug
  - [x] agent_gate round_106 冒烟

### Round 107 - Phase5 收口摘要

- 目标：聚合 round_103–106 预研模块状态，文档收口。
- 范围：`phase5_closure_summary.py`、`docs/phase5_closure.md`、API。
- 非目标：新平台实现；改微信主线。
- 输入：Phase5 各 dry-run 模块。
- 输出：`phase5-closure-summary`；`/api/phase5/closure-summary`。
- 验收标准：`test_phase5_closure` 通过。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_phase5_closure.py -q`。
- 退出标准：gate round_107。
- 风险：无。
- 回滚点：移除 closure API。
- 交付项：
  - [x] Phase5 收口 API 与文档
  - [x] agent_gate round_107 冒烟

### Round 108 - 微信 P0 主线小步强化

- 目标：Phase5 收口后回到微信公众号主线；overview/预检/队列/status 真实体验改进。
- 范围：`generation_policy`、`workbench_mvp` 预检联动、`queue-summary`、首页 UI。
- 非目标：Phase5 新平台；改 cron；真实联网发布。
- 输入：round_101 链路提示、round_041 预检。
- 输出：顶部 `AUTO_APPROVE` 标识；下一步联动预检失败；队列摘要含 `preflight_ready`。
- 验收标准：`test_round_108_wechat_p0`；mock@8080 浏览器走首页→主操作→队列。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_108_wechat_p0.py -q`。
- 退出标准：gate round_108。
- 风险：无。
- 回滚点：恢复 workbench 无 preflight 参数。
- 交付项：
  - [x] status/overview 预检与 AUTO_APPROVE
  - [x] 队列摘要强化
  - [x] agent_gate round_108 冒烟

### Round 109 - 微信 P0 续（预检条与失败队列）

- 目标：作品库/详情预检条与 blocking 联动；失败队列 Tab 强化重试与错误摘要。
- 范围：`article_preflight`、`queue_display`、`admin_template`、作品详情页。
- 非目标：真实联网发布；Phase5 新平台。
- 输入：round_108 预检与队列摘要。
- 输出：作品 API `preflight_bar`；详情顶栏预检；失败 Tab 横幅与批量重试；`failed_preview`/`failure_digest`。
- 验收标准：`test_round_109_wechat_p0`；mock@8080 浏览器走作品卡→详情→失败队列。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_109_wechat_p0.py -q`。
- 退出标准：gate round_109。
- 风险：无。
- 回滚点：移除作品 preflight_bar 与队列 failed_preview。
- 交付项：
  - [x] 作品预检条与 blocking 联动
  - [x] 队列失败 Tab 重试与错误摘要
  - [x] agent_gate round_109 冒烟

### Round 110 - 执行到点与预检 blocking 联动

- 目标：「执行到点发布」与 `publish_preflight` blocking 联动；run-once 结果 toast 并刷新事件区。
- 范围：`publish_preflight.run_once_gate`、`/api/run-once` 服务端拦截、工作台 `btnRun` UI。
- 非目标：真实联网发布；Phase5 新平台。
- 输入：round_108–109 预检与队列体验。
- 输出：按钮禁用+原因文案；run-once toast/resultBox；事件区高亮刷新；API 预检阻断。
- 验收标准：`test_round_110_wechat_p0`；mock@8080 点击「执行到点发布」。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_110_wechat_p0.py -q`。
- 退出标准：gate round_110。
- 风险：无。
- 回滚点：移除 run_once_gate 与按钮禁用逻辑。
- 交付项：
  - [x] 预检 blocking 禁用执行到点
  - [x] run-once toast 与事件刷新
  - [x] agent_gate round_110 冒烟

### Round 111 - 生成排期与待人工确认入口

- 目标：「生成排期」与 `plan_gate` 预检联动；首页展示 `waiting_confirmation` 入口。
- 范围：`publish_preflight.plan_gate`、`/api/plan`、`overview`、`admin_template` 队列筛选。
- 非目标：真实联网；新 proof 流程。
- 输入：round_110 run_once_gate、既有 `/api/waiting-confirmation`。
- 输出：生成排期按钮禁用+原因；概览待确认卡片；队列「待人工确认」Tab。
- 验收标准：`test_round_111_wechat_p0`；mock@8080 点击生成排期/待确认入口。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_111_wechat_p0.py -q`。
- 退出标准：gate round_111。
- 风险：无。
- 回滚点：移除 plan_gate 与 waitingConfirmEntry。
- 交付项：
  - [x] 生成排期预检联动
  - [x] 待人工确认首页入口
  - [x] agent_gate round_111 冒烟

### Round 112 - 扫描收件箱反馈与链路联动

- 目标：「扫描本地收件箱」toast/摘要增强，与 `chain_summary` 联动；扫描前轻量 inbox 预检。
- 范围：`scan_preflight`、`scan_summary`、`/api/scan`、`admin_template`。
- 非目标：真实联网；收件箱解析规则变更。
- 输入：round_091 chain_summary、既有 `scan_inbox`。
- 输出：`scan_summary`/`chain_hint`；`GET /api/scan-preflight`；概览 `#chainScanHint`。
- 验收标准：`test_round_112_wechat_p0`；mock@8080 点击扫描。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_112_wechat_p0.py -q`。
- 退出标准：gate round_112。
- 风险：无。
- 回滚点：恢复 scan 简单 human 返回。
- 交付项：
  - [x] 扫描反馈与 chain 联动
  - [x] inbox 路径预检
  - [x] agent_gate round_112 冒烟

### Round 113 - 待确认快速 proof

- 目标：待人工确认队列 Tab 内快速提交 mock dry-run 占位 proof；列表跳转详情 `#proof`。
- 范围：`proof_quick`、`/api/waiting-confirmation`、`admin_template` 队列 Tab。
- 非目标：真实联网 proof 校验。
- 输入：round_111 待确认入口、proof API。
- 输出：`quick_dry_run` proof；`quick-proof-all`；AUTO_APPROVE 横幅；填写证明/快速确认按钮。
- 验收标准：`test_round_113_wechat_p0`；mock@8080 待确认 Tab 点击。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_113_wechat_p0.py -q`。
- 退出标准：gate round_113。
- 风险：无。
- 回滚点：移除 quick proof API 与 Tab 按钮。
- 交付项：
  - [x] 快速 proof 与批量确认
  - [x] 详情 proof 锚点跳转
  - [x] agent_gate round_113 冒烟

### Round 114 - 上传反馈与 outbox 快捷导出

- 目标：上传 .md 后 toast/摘要 + scan 联动；作品卡一键导出 outbox。
- 范围：`upload_summary`、`/api/upload`、`admin_template` 作品卡按钮。
- 非目标：outbox 格式变更。
- 输入：round_112 scan 联动、既有 `export-outbox` API。
- 输出：`upload_summary`/`chain_hint`；`showUploadOutcome`；`导出 outbox` 按钮。
- 验收标准：`test_round_114_wechat_p0`；mock@8080 上传与导出点击。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_114_wechat_p0.py -q`。
- 退出标准：gate round_114。
- 风险：无。
- 回滚点：恢复简单 upload human。
- 交付项：
  - [x] 上传 scan 联动反馈
  - [x] 作品卡导出 outbox
  - [x] agent_gate round_114 冒烟

### Round 115 - 仓库卫生与维护冒烟

- 目标：忽略本地 outbox 测试包、Playwright 诊断与 r114 测试稿；扩展维护冒烟覆盖 round_114 API。
- 范围：`.gitignore`、`test_round_102_maintenance_smoke`。
- 非目标：删除用户真实 `articles/` 数据；提交业务 outbox 包。
- 输入：round_114 上传/导出 API。
- 输出：`outbox/*`、`.playwright-mcp/`、`articles/imported/r114_*` 忽略规则；上传+export-outbox 冒烟。
- 验收标准：`test_round_102` 新用例；`git status` 无密钥；mock@8080 首页。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_102_maintenance_smoke.py -q`。
- 退出标准：gate round_115。
- 风险：无。
- 回滚点：移除新增 gitignore 行。
- 交付项：
  - [x] .gitignore 卫生规则
  - [x] 维护冒烟扩展
  - [x] agent_gate round_115 冒烟

### Round 116 - 高级信息持久化

- 目标：「显示高级信息」写入 localStorage；默认隐藏 /debug 入口与帮助区开发者链接、内部 JSON 面板。
- 范围：`admin_template.html` 开关、导航、帮助、`:root.show-advanced` CSS。
- 非目标：/debug 页面功能变更。
- 输入：AGENTS.md 普通用户视图原则。
- 输出：`wechat_workbench_show_advanced`；`advanced-only` 包裹 debug 链接。
- 验收标准：`test_round_116_wechat_p0`；mock@8080 开关刷新保持。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_116_wechat_p0.py -q`。
- 退出标准：gate round_116。
- 风险：无。
- 回滚点：移除 localStorage 与 advanced-only 导航类。
- 交付项：
  - [x] localStorage 持久化
  - [x] 默认隐藏 debug/JSON
  - [x] agent_gate round_116 冒烟

### Round 117 - 合集筛选持久化

- 目标：作品库「合集」下拉写入 localStorage，刷新后恢复；Desktop-first 无横向溢出。
- 范围：`collectionFilter`、`initCollectionFilter`、`loadCollectionFilterOptions`。
- 非目标：合集数据模型变更。
- 输入：round_116 Desktop-first、`GET /api/collections`。
- 输出：`wechat_workbench_collection_slug`；无效 slug 自动清空。
- 验收标准：`test_round_117_wechat_p0`；`test_ordinary_view_e2e_baseline`；mock@8080。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_117_wechat_p0.py -q`。
- 退出标准：gate round_117。
- 风险：无。
- 回滚点：移除合集 localStorage 逻辑。
- 交付项：
  - [x] 合集筛选 localStorage
  - [x] 刷新恢复与无效 slug 清理
  - [x] agent_gate round_117 冒烟

### Round 118 - 队列 Tab 筛选持久化

- 目标：发布队列「待发布/失败/…」Tab 写入 localStorage，刷新后恢复。
- 范围：`queueFilters`、`initQueueFilter`、`setQueueFilterKey`。
- 非目标：队列 API 语义变更。
- 输入：round_117 持久化模式、`GET /api/jobs?status=`。
- 输出：`wechat_workbench_queue_filter`；统计卡跳转同步持久化。
- 验收标准：`test_round_118_wechat_p0`；mock@8080 Tab 切换与刷新。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_118_wechat_p0.py -q`。
- 退出标准：gate round_118。
- 风险：无。
- 回滚点：恢复 `setupQueueFilters` 无 localStorage。
- 交付项：
  - [x] 队列 Tab localStorage
  - [x] 刷新恢复与无效 key 回退
  - [x] agent_gate round_118 冒烟

### Round 119 - Hash 深链与区块恢复

- 目标：`#queue`/`#works`/`#drafts` 深链；刷新恢复当前区块；与 queue/collection localStorage 协同。
- 范围：`initWorkbenchHash`、`navigateWorkbenchSection`、head 预恢复 hash。
- 非目标：独立路由页改造。
- 输入：round_117/118 localStorage 模式。
- 输出：`wechat_workbench_section_hash`；`#articles`→`#works` 别名。
- 验收标准：`test_round_119_wechat_p0`；mock@8080 `/#queue` 直达。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_119_wechat_p0.py -q`。
- 退出标准：gate round_119。
- 风险：无。
- 回滚点：恢复 `setupNav` 无 hash 持久化。
- 交付项：
  - [x] hash 深链与 localStorage
  - [x] 刷新恢复区块
  - [x] agent_gate round_119 冒烟

### Round 120 - 详情返回保留工作台上下文

- 目标：详情页「返回工作台」带回来源 hash；queue/collection localStorage 仍生效。
- 范围：`captureWorkbenchReturnContext`、`article_detail` 返回链接。
- 非目标：详情页路由改造。
- 输入：round_119 hash、round_117/118 localStorage。
- 输出：`wechat_workbench_return_hash` session；`workbenchReturnUrl()`。
- 验收标准：`test_round_120_wechat_p0`；mock@8080 队列→详情→返回。
- 建议测试/冒烟命令：`.venv/bin/python -m pytest tests/test_round_120_wechat_p0.py -q`。
- 退出标准：gate round_120。
- 风险：无。
- 回滚点：恢复 `href="/"` 静态返回。
- 交付项：
  - [x] 进入详情捕获返回上下文
  - [x] 详情返回动态 hash 链接
  - [x] agent_gate round_120 冒烟

## 历史说明

历史实现细节见提交记录；逐轮完成报告已在 Round 43 精简移除，避免仓库堆积冗余文档。
