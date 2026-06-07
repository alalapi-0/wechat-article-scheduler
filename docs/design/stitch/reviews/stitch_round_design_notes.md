# Stitch Round Design Notes

## 任务

本轮设计任务是微信公众号本地发布工作台 Dashboard 的首屏“安全状态与下一步”区域。目标用户是不懂编程的个人公众号作者，目标是在进入页面后先确认当前是否安全，再知道下一步应该点哪个按钮。

## Stitch 可用性

- `.cursor/mcp.json` 已配置 `stitch` remote MCP。
- `.env.example` 已提供 `STITCH_API_KEY` 占位。
- 本轮环境中 `STITCH_API_KEY` 已设置，但可用 MCP descriptor 目录中没有直接列出的 `stitch` 工具 descriptor。
- 按“调用 MCP tool 前必须读取 descriptor”的要求，本轮未直接调用 Stitch tool。
- fallback 设计依据来自 `docs/design/DESIGN.md`、`docs/design/stitch/UI_TASKS.md` 和 `docs/design/stitch/PROMPT_TEMPLATES.md`。

## 采用的设计结构

- 顶部保持现有轻导航和安全 pill。
- Hero 下方新增 `safety-dashboard`，作为首屏核心判断区。
- 左侧展示模式、到点执行状态、下一步 headline、解释文案和主操作按钮。
- 右侧展示四个关键数字：已收录作品、待发布任务、失败任务、微信草稿记录。
- 底部展示三步流程 rail：找文章、安排时间、执行到点。
- 右侧原有“主操作”三步卡片同步高亮当前推荐步骤。

## 采用的文案原则

- 使用“演练模式 · 不会真的发到公众号”解释 mock。
- 使用“真实连接 · 仅创建草稿，不会发布”解释 draft-only。
- 使用“真实 API 测试 · 正式发布任务会真的发”解释真实发布风险。
- 主按钮根据现有 `workbench.primary_action` 切换为扫描、上传、生成排期、查看队列、执行到点或刷新。
- 不显示数据库路径、原始 JSON、内部状态枚举；这些仍留在高级信息。

## 与现有系统的映射

- `renderDashboard(ov, dsum)` 复用 `refreshAll()` 已加载的聚合数据。
- `dashboardMode()` 复用 `publish_policy` 和 `publish_preflight`。
- `dashboardPrimaryConfig()` 复用 `onScan()`、`onPlan()`、`onRun()`、`refreshAll()` 与现有导航。
- `stepKeyFromPrimary()` 把推荐动作映射到三步流程高亮。

## 拒绝或调整的建议

- 没有引入侧边栏重构，因为当前导航已可用，且本轮目标是一个高优先级切片。
- 没有新增后端接口，避免扩大行为面。
- 没有把“审核台”作为本轮主切片，因为当前权威路线已移除内容审核概念，proof 只是发布证明。
- 没有生成或提交大截图、导出 HTML 或外部设计文件。

## 浏览器验收路径

1. 打开 `http://127.0.0.1:8080/`。
2. 检查 `safety-dashboard`、模式 pill、主按钮、三步 rail、四个计数。
3. 在空库状态下点击主按钮或扫描按钮，确认安全门控和反馈正常。
4. 检查作品库、队列、草稿、事件仍正常渲染。
5. 检查 1280、768、375 宽度无整页横向溢出。
6. 检查 console 无严重 error，network 核心 API 无失败。
