# 设计输入总则

本目录是微信公众号本地工作台的设计输入层。权威产品边界仍由 `docs/product_vision.md`、`docs/ordinary_user_workbench_principles.md`、`docs/info_layer_boundary.md` 和 `docs/web_console_design.md` 决定；Stitch 不能改变业务范围。

## 当前产品约束

- 面向个人用户的本地微信公众号草稿、排期和发布辅助工作台。
- 普通视图优先回答：现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办。
- Desktop-first，主验收视口约为 `1280x900`；窄屏只要求可读、可点、无整页横向溢出。
- 数据库路径、原始 JSON、内部 id、调试统计默认放进高级信息。
- 技术栈保持 `FastAPI + 原生 HTML/CSS/JS`，不因设计稿擅自引入 React/Vue 或新的 UI 框架。
- 默认 `WECHAT_MODE=mock`；界面必须明确区分 mock、dry-run、真实 API 和草稿-only。

## Stitch 的角色

Stitch 用于生成页面方案、screen、variants、截图、HTML 和设计系统建议。它只提供设计输入：

1. 先用 `docs/design/stitch/UI_TASKS.md` 定义任务。
2. 用 `docs/design/stitch/PROMPT_TEMPLATES.md` 形成 prompt。
3. 将导出物保存到 `docs/design/stitch/`。
4. 人工或 Agent 评审后，拆成符合现有代码结构的小任务。
5. 实现后用 Playwright 或 chrome-devtools 检查真实页面、console、network 和核心流程。

不得把 Stitch HTML 直接覆盖业务页面，也不得把视觉方案当作业务规则、权限结论或 API 能力证明。

## 设计交付最低要求

- 页面目标、目标用户和核心流程清楚。
- 普通/详情/高级信息边界明确。
- loading、empty、success、warning、error、disabled 状态完整。
- 中文文案可直接用于个人用户，不暴露裸内部枚举。
- 桌面表格密度与批量操作优先，响应式不破坏关键操作。
- 评审记录说明采用、调整和拒绝了哪些 Stitch 建议。
