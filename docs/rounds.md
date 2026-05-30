# 开发轮次（Round 0 ~ Round 9）

机器可读状态见 `governance/round_state.yaml`。  
机器可读轮次注册表见 `scripts/agent_gate.py` 的 `ROUND_ORDER` / `ROUND_META`，须与本表保持一致。  
本文件为**权威路线图**，明确“已实现 / 部分实现 / 设计中 / 未来计划”。

| Round | 轮次主题 | 状态 | 主要目标 |
|------|---------|------|---------|
| Round 0 | CLI MVP 闭环 | 已实现 | init-db/scan/plan/run-once 基线 |
| Round 1 | 治理轮 | 已完成 | 全仓审计、文档重构、120 digest 统一、骨架补齐 |
| Round 2 | 内容库建模 | 进行中 | 内容集合、标签、审核状态与索引 |
| Round 3 | 调度域模块化 | 设计中 | scheduler 领域拆分与执行器分层 |
| Round 4 | 数据迁移体系 | 设计中 | migrations 版本化、回滚策略、兼容升级 |
| Round 5 | Web 控制台增强 | 未来计划 | 轻量鉴权、只读仪表盘、人工确认流 |
| Round 6 | 渲染与模板扩展 | 未来计划 | Markdown/HTML 渲染规则与模板策略 |
| Round 7 | 封面资产管理 | 未来计划 | 素材目录、引用与人工裁剪流程 |
| Round 8 | 可观测与运维 | 未来计划 | 更细粒度审计、失败分类、SLO 指标 |
| Round 9 | 发布工作台产品化 | 未来计划 | 稳定交付、文档收口、长期维护规范 |

## Round 1 交付要点（治理轮）

- 全量扫描仓库能力与风险，形成 `docs/current_state_audit.md`
- 项目重定位为“本地微信公众号文章发布工作台”
- 新增产品愿景、迁移计划、能力矩阵与专题设计文档
- 创建 `content_library` / `renderers` / `scheduler` / `cover_assets` 等目录骨架
- 摘要上限统一到 120，上传前自动截断并记录 warning 事件
- 新增两类最小测试：digest 截断与 Markdown 段落渲染

## 历史说明

历史实现细节可参考 `docs/reports/` 下各轮完成报告与 Git 提交记录。
