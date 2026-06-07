# UX-LOOP-001 用户视角测试报告

## 1. 本轮结论

- 是否存在 P0：否
- 是否存在 P1：是（已在本轮修复）
- 是否需要自动修复：是
- 是否允许停止循环：否
- 当前最高问题等级：P1（修复前）/ P2（修复后）
- 本轮是否已使用浏览器工具：是（Playwright）
- 本轮是否已检查 UI 美观性：是

## 2. 测试环境

- 操作系统：darwin 25.3.0
- Python 版本：3.14.5
- Node 版本：v26.0.0
- 启动命令：`WECHAT_MODE=mock WECHAT_ENABLE_PUBLISH=false WEB_AUTO_PUBLISH=false DATABASE_PATH=/tmp/wcas-ux-loop.sqlite3 .venv/bin/python -m wechat_article_scheduler.cli serve --host 127.0.0.1 --port 8081`
- 页面地址：http://127.0.0.1:8081/ 、http://127.0.0.1:8082/（修复后回归）
- WECHAT_MODE：mock
- WECHAT_ENABLE_PUBLISH：false
- DATABASE_PATH：/tmp/wcas-ux-loop.sqlite3（首轮）/ /tmp/wcas-ux-loop2.sqlite3（修复回归）
- 使用的 MCP 工具：Playwright、filesystem（等效 Read/Write/Grep）
- 测试时间：2026-06-07 20:08–20:14 CST

## 3. 实际测试路径

1. 读取 README、AGENTS.md、.env.example；
2. 初始化隔离 DB 与 `/tmp/wcas-ux-inbox`；
3. 启动 Web 服务（8080 已有实例对照 + 8081 隔离实例）；
4. 打开首页，等待 API 加载，检查模式条与下一步引导；
5. 创建测试 Markdown（正常 / 空 / 无标题），CLI scan；
6. CLI plan + Web「扫描本地收件箱」+「执行到点草稿创建」；
7. 查看队列与统计卡片更新；
8. 打开 `/articles/1` 详情，检查下一步、发布状态、预览；
9. 检查外部 Agent 区域与导出菜单；
10. 检查 console / network（无 error）；
11. 375px / 1280px 视口截图；
12. 评估美观性与文案（mock/draft-only 区分）。

## 4. 功能通过情况总览

| 模块 | 是否通过 | 问题等级 | 用户体验评价 | 说明 |
|---|---|---|---|---|
| 启动 | 是 | — | 良好 | venv + serve 正常 |
| 首页 | 是 | P2 | 较好 | 有三步引导；首屏短暂 loading |
| Dashboard | 是 | P2 | 较好 | 模式条清晰；信息略密 |
| 上传 | 是 | P1→已修 | 良好 | 空文件 scan 拒绝；上传反馈补 skipped_empty |
| 扫描 | 是 | — | 良好 | 空文件 errors+skipped_empty |
| 空文件 | 是 | — | 良好 | 不入库 |
| 文章列表 | 是 | — | 良好 | 2 篇测试文可见 |
| 文章详情 | 部分 | P1→已修 | 修复前混乱 | done 任务仍显示「尚未安排发布时间」 |
| 排期 | 是 | — | 良好 | plan 正常 |
| 队列 | 是 | — | 良好 | 状态可读 |
| run-once | 是 | — | 良好 | mock 草稿创建成功 |
| 草稿记录 | 是 | P1→已修 | 良好 | next_hint 文案已改为「更新草稿」 |
| 外部 Agent 任务包 | 是 | P2 | 可用 | 浏览器辅助会话可启动；CLI export 有测试覆盖 |
| proof | 未测 | P2 | — | 本轮无 waiting_confirmation 任务 |
| 状态持久化 | 是 | — | 良好 | 刷新后保持 |
| console | 是 | — | 无 error | |
| network | 是 | — | 核心 API 200 | |
| 响应式 | 是 | P2 | 可接受 | 375px 可读，未严重溢出 |
| 美观性 | 是 | P2 | 6–7/10 | 像正式工具，非 debug 面板 |
| 文案清晰度 | 部分 | P1→已修 | 改善 | publish/auto_publish 语义、详情按钮 |
| mock / real 区分 | 部分 | P1→已修 | 改善 | publish_policy 增加 effective/ignored |

## 5. UI / UX / 美观性评估

### 首页 / Dashboard

- 美观评分 1-10：7
- 是否像正式产品：是
- 是否像 debug 页面：否
- 主要问题：首屏短暂「正在读取…」；高级区信息偏多
- 建议：保持当前三步卡片，后续可优化 loading skeleton

### 文章列表

- 美观评分 1-10：7
- 可读性：良好
- 状态清晰度：良好
- 主要问题：表格在文章多时可能偏密
- 建议：维持当前状态标签体系

### 文章详情

- 美观评分 1-10：6（修复前）/ 8（修复后）
- 预览体验：良好
- 预检体验：良好
- 主要问题：修复前下一步与发布状态矛盾；「去工作台安排发布」误导
- 建议：已修复 done 任务文案与按钮

### 队列 / 草稿

- 美观评分 1-10：7
- 状态清晰度：良好
- 操作清晰度：良好
- 主要问题：草稿 next_hint 曾写「执行发布」
- 建议：已改为 draft-only 文案

### 任务包 / proof

- 美观评分 1-10：7
- 是否容易理解：是
- 是否容易操作：是
- 主要问题：proof 本轮未走到 waiting_confirmation
- 建议：下轮构造该状态回归

## 6. 问题清单

### P1-001

- 等级：P1
- 模块：配置 / API 状态
- 类型：文案 / 安全
- 问题描述：`WECHAT_ENABLE_PUBLISH=false` 时 API 仍返回 `web_auto_publish=true`（8080 用户 .env），与 `publish_enabled=false` 语义冲突
- 复现步骤：启动服务后 GET `/api/status`
- 预期结果：用户能判断自动发布是否真正生效
- 实际结果：raw `web_auto_publish` 与 `publish_enabled` 矛盾
- 用户影响：误以为会自动发布
- 可能原因：`publish_policy` 未暴露有效语义
- 建议修复方向：增加 `web_auto_publish_effective` / `web_auto_publish_ignored` 与 env_hint
- 是否必须本轮修复：是
- 是否需要测试覆盖：是（已加）

### P1-002

- 等级：P1（降级为已满足）
- 模块：扫描 / 上传
- 类型：数据
- 问题描述：空 Markdown 可能被导入
- 复现步骤：scan 空文件
- 预期结果：拒绝入库
- 实际结果：scan 已 `skipped_empty`；上传人话摘要未提示空文件
- 用户影响：上传空文件后困惑
- 建议修复方向：合并 skipped_empty 统计并提示
- 是否必须本轮修复：是（上传反馈）
- 是否需要测试覆盖：间接覆盖

### P1-003

- 等级：—（未复现）
- 模块：weekly plan
- 类型：功能
- 问题描述：连续 plan 重复排期
- 实际结果：`test_weekly_plan_three_weeks_zero_repeat` 存在；本轮小样本 plan 正常
- 是否必须本轮修复：否

### P1-004

- 等级：P2
- 模块：real API 预检
- 类型：文案
- 问题描述：无凭证环境无法 E2E real
- 实际结果：mock 模式预检明确；real 需凭证（符合设计）
- 是否必须本轮修复：否

### P1-005

- 等级：P1
- 模块：文章详情
- 类型：UX / 文案
- 问题描述：任务 `done` 且已有草稿时，下一步仍显示「尚未安排发布时间」
- 复现步骤：run-once 后打开 `/articles/{id}`
- 预期结果：提示草稿已创建、下一步去后台核对
- 实际结果：与发布状态区块矛盾
- 是否必须本轮修复：是
- 是否需要测试覆盖：是（已加）

### P1-006

- 等级：P1
- 模块：文案
- 类型：文案
- 问题描述：多处「执行发布/安排发布」与 draft-only 主线不符
- 是否必须本轮修复：是

### P2-001

- 等级：P2
- 模块：首页 loading
- 类型：UX
- 问题描述：首屏短暂「正在读取运行状态…」
- 是否必须本轮修复：否

### P4-001

- 等级：P4
- 模块：导出
- 类型：文案
- 问题描述：多平台预研导出入口可能干扰主线
- 是否必须本轮修复：否

## 7. P0/P1 自动修复任务清单

### 修复任务 1

- 对应问题：P1-001
- 目标：澄清 web_auto_publish 有效语义
- 涉及文件：`publish_policy.py`, `app.py`
- 修改方向：增加 effective/ignored 字段与 env_hint
- 验收标准：`/api/status` 在 publish off + web_auto_publish on 时 ignored=true
- 回归测试：`test_global_policy_ignores_web_auto_publish_when_publish_off`
- 优先级：高

### 修复任务 2

- 对应问题：P1-005, P1-006
- 目标：详情页 done 任务下一步与按钮文案
- 涉及文件：`article_detail.py`, `article_detail_template.html`, `drafts_display.py`, `admin_template.html`
- 验收标准：done+草稿显示「草稿已创建…」；按钮「返回工作台」
- 回归测试：`test_suggest_detail_actions_done_job_with_draft`
- 优先级：高

### 修复任务 3

- 对应问题：P1-002 上传反馈
- 目标：空文件跳过人话提示
- 涉及文件：`scanner.py`, `uploads.py`
- 验收标准：upload/scan 返回 skipped_empty 提示
- 优先级：中

## 8. Console / Network 记录

- console error：无
- network error：无
- 失败请求：无（核心 `/api/*` 均 200）
- 静态资源问题：无
- 截图：`docs/reports/ux_loop/UX-LOOP-001_detail_fixed.png`

## 9. 工具使用证明

| 工具 | 是否实际使用 | 用途 | 结果 |
|---|---|---|---|
| filesystem | 是 | 读文档、写报告、改代码 | 完成 |
| playwright | 是 | 首页/详情/点击/截图/console | 完成 |
| context7 | 否 | 本轮无库用法疑问 | — |
| stitch | 否 | UI 未达 P0 丑陋阈值 | — |
| github | 否 | 本轮末尾 push 用 git CLI | 待 push |

## 10. 本轮是否进入修复

- 是否进入修复：是
- 进入原因：存在 P1-001/005/006 与上传反馈缺口
- 修复范围：publish_policy、详情下一步、文案、upload skipped_empty
- 修复后测试命令：`pytest`（459 passed）、`agent_gate gate`（PASS）
- 修复后是否通过：是

## 11. 下一轮重点

1. 全量用户路径再跑一遍（上传→scan→plan→run-once→详情→刷新）
2. 验证用户 .env 中 `WEB_AUTO_PUBLISH=true` 时 UI 是否展示 ignored 提示
3. proof / waiting_confirmation 流程
4. 外部 Agent 任务包文件完整性（task.json 等）
5. 移动端 375/768 完整回归
6. 首页 loading 体验（P2）
7. 多平台导出入口是否需降级到高级区（P4）
8. 队列失败重试路径
9. 空状态首页美观性
10. real 模式预检文案（无凭证）
