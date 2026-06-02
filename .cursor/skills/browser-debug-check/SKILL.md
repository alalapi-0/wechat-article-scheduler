---
name: browser-debug-check
description: 修改前端页面、审核页面、浏览器交互、文件管理 UI、API 调用、生成内容预览 UI 后，必须执行浏览器级验证、console/network 检查和回归确认。
---

# Browser Debug Check

## 目标

本技能用于防止 Agent 只凭代码或页面表面效果判断任务完成。

每次涉及以下内容时，必须执行完整验证闭环：

- 前端页面
- 审核工作台
- 浏览器交互
- 文件上传、删除、移动、保存
- API 请求
- 本地生成内容预览
- 数据库读写
- 生成内容审核流程

## 必须流程

1. 阅读项目根目录的关键文档：
   - `AGENTS.md`
   - `README.md`
   - `docs/`
   - `.cursor/rules/`
2. 确认当前任务目标、禁止事项和验收标准。
3. 启动项目开发服务。
4. 使用 Playwright MCP 或 Chrome DevTools MCP 打开目标页面。
5. 执行至少一个真实用户路径，例如：
   - 打开审核页面
   - 查看一条数据
   - 放大预览
   - 删除或移动测试数据
   - 保存设置
   - 刷新页面确认状态是否持久化
6. 检查浏览器 console：
   - 不允许存在 error；
   - warning 需要记录并判断是否可接受。
7. 检查 network：
   - 不允许核心 API 请求失败；
   - 对 4xx / 5xx 必须解释原因。
8. 保存或查看页面 snapshot / screenshot，确认 UI 变化真实出现。
9. 执行项目验证命令：
   - `npm run lint`，如果存在；
   - `npm run test`，如果存在；
   - `npm run build`，如果存在；
   - `npm run agent:check`，如果存在。
10. 如果任何一步失败，必须先修复，再重新执行验证。
11. 最后输出验证报告。

## 输出格式

必须输出：

- 修改了哪些文件
- 验证了哪些用户路径
- console 是否有 error
- network 是否有失败请求
- build/test/lint 是否通过
- 仍然存在的风险
- 下一轮建议

## 禁止

- 禁止只说“看起来正常”
- 禁止未打开浏览器就判断前端任务完成
- 禁止未检查 console/network 就说无错误
- 禁止未验证文件系统真实变化就说删除/移动功能完成
- 禁止把 mock 数据测试结果当作真实 API 测试结果
- 禁止忽略失败的测试、构建、console error、network error
