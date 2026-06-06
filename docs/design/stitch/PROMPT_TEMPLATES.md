# Stitch Prompt 模板

所有模板都要补齐方括号。默认中文 UI、浅色、桌面优先；若现有页面已有明确主题，应沿用而非重做品牌。

## Dashboard

```text
为“微信公众号文章本地调度器”设计一个个人用户 Dashboard。目标用户是不懂编程的公众号作者。
采用 Desktop-first 1280x900 布局，左侧导航、顶部安全状态、主内容区。
核心组件：mock/dry-run/real_api/草稿-only 状态条，找文章->安排时间->执行到点文章三步流程，最近结果，待办摘要，失败任务和恢复建议，文章/队列/草稿/事件入口。
提供 loading、empty、success、warning、error、disabled 状态。中文文案用人话，原始 JSON、数据库路径和内部字段放进高级信息。
浅色、克制、工作台风格。不要生成营销首页、团队 SaaS、数据大屏或无关多平台功能。
设计必须能由 FastAPI + 原生 HTML/CSS/JS 实现。
```

## Review Workbench

```text
为微信公众号文章设计 Review Workbench。用户需要核对正文、摘要、封面、合集、草稿状态和 proof。
桌面双栏：左侧文章与公众号近似预览，右侧字段检查、风险提示和操作；底部为默认折叠的日志与元数据。
必须显示 mock/dry-run/real_api/draft-only，提供通过、退回、移出流程和删除二次确认。
覆盖无封面、摘要过长、远端草稿失效、API 无权限、proof 缺失等状态。中文 UI，普通信息优先，高级字段折叠。
不要替用户点击最终发布，不要生成营销页面，不要引入当前项目之外的审批组织结构。
```

## Visual Review

```text
为[未来视觉内容项目]设计视觉结果审核台，目标用户是单人创作者。
桌面布局包含缩略图 grid、选中结果大图/视频、prompt 摘要、质量评分、一致性检查、失败重试、通过/驳回/重新生成。
明确 real_api/mock/dry-run 和文件来源，覆盖 loading、空结果、部分失败、素材损坏状态。
中文 UI，深浅主题偏好为[填写]。不要生成营销页。此模板不是当前微信公众号 P0，使用前必须确认路线图已启用该能力。
```

## Game Asset Gallery

```text
为[未来游戏资产项目]设计 Game Asset Gallery。
核心组件：角色图、sprite sheet、动画帧时间轴、透明背景检查、尺寸/帧对齐检查、版本与导出操作。
桌面优先，支持筛选和批量审核，状态包含生成中、检查失败、可导出、已驳回。
中文 UI，设计服务真实资产管线，不生成游戏商店或营销站。使用前确认该项目类型与路线图。
```

## Video Preview Workbench

```text
为[未来视频生成项目]设计 Video Preview Workbench。
展示图片输入、文字 prompt、镜头列表、生成进度、视频播放器、关键帧/抽帧、失败镜头和单镜头重试。
提供版本对比、连续性检查、通过/驳回，不允许把 mock 结果标成 real_api。
中文 UI，桌面编辑工作台，不生成视频平台首页或营销页。使用前确认路线图已启用视频能力。
```

## Debug Panel

```text
为微信公众号本地调度器设计开发者 Debug / Observability 页面。
展示 API health、scheduler health、任务队列、文件扫描状态、远端草稿同步、console/network 错误摘要和最近操作日志。
支持按时间/任务/文章筛选，复制脱敏诊断摘要，跳转关联对象。token、secret、cookie、完整 Authorization 永不显示。
该页只属于高级信息，不占普通用户首屏。中文 UI，桌面高密度表格，不做炫技数据大屏。
```

## Mobile Responsive

```text
将[页面名称]适配到 768px 和 375px，但保持 Desktop-first。
目标仅为无整页横向溢出、文字可读、关键按钮可点、风险确认不丢失。允许表格容器内滚动或顺序堆叠。
不要把桌面高密度任务队列重做成信息缺失的卡片流，不要隐藏安全状态、主操作和错误恢复。
输出 desktop/tablet/mobile 三种 screen，并说明响应式取舍。
```
