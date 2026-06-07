# Stitch Round Design Tokens

本轮没有直接导入 Stitch HTML；以下 token 是从 Stitch Dashboard prompt、现有工作台风格和 `docs/design/DESIGN.md` 约束整理后手工落地的设计输入。

## Layout

- `max-width`: 1240px，沿用主工作台宽度。
- `safety-dashboard`: 两栏桌面布局，左侧状态与行动，右侧关键计数。
- `desktop breakpoint`: 大于 1050px 保持两栏。
- `tablet/narrow`: 1050px 以下堆叠，760px 以下计数和流程 rail 单列。
- `spacing`: 首屏卡片 16px padding，卡片间距 14px，主内容间距 18px。

## Color

- `--bg`: `#fbfbfa`，浅暖背景。
- `--surface`: `#ffffff`，主卡片底色。
- `--surface-soft`: `#f6f6f4`，轻强调底色。
- `--surface-warm`: `#faf7f0`，Dashboard 渐变终点与提示底色。
- `--accent`: `#2f3437`，主按钮和当前步骤。
- `--ok`: `#287a4b`，mock 安全/成功状态。
- `--warn`: `#9a6b17`，真实草稿-only、警示状态。
- `--err`: `#a33a32`，真实发布风险、阻断状态。
- `--line`: `#e8e6e1`，轻边框。

## Typography

- 字体沿用系统 sans：`ui-sans-serif`, `-apple-system`, `PingFang SC`, `Microsoft YaHei`。
- Dashboard headline: 20px，`line-height: 1.25`。
- 主标题: 26px，保留现有 Hero。
- 正文提示: 13px。
- 数字计数: 20px，紧凑行高。

## Components

- `pill`: 保持现有 pill 体系，并复用 `ok`、`warn`、`err`。
- `safety-metric`: 小卡片显示数字和标签，不展示内部字段。
- `flow-step`: 三步流程 rail，当前步骤用边框和内阴影强调。
- `step.current`: 右侧主操作卡片同步高亮，编号背景切换为 accent。
- `dashboardPrimaryAction`: 复用按钮样式，行为映射到已有安全函数。

## States

- Loading: 初始文案“正在读取模式…”、“读取当前工作台状态…”。
- Empty: 空库时主按钮引导上传或扫描；作品库和队列保留原空状态。
- Safe mock: 绿色 `ok`。
- Draft-only real: 黄色 `warn`。
- Real publish enabled: 红色 `err`。
- Preflight blocked: headline 与状态文本保留发布前检查阻断信息，主操作继续复用原门控。

## Responsive Rules

- 1280x900：Dashboard 两栏，右侧计数 2x2，流程三列。
- 768 宽：Dashboard 单列，仍保留模式、主按钮和计数。
- 375 宽：计数与流程单列；不隐藏安全状态、主按钮或错误提示。

## Security

- 不展示 `.env`、API key、token、cookie。
- 不展示数据库路径和原始 JSON。
- 不新增真实发布绕过路径；真实发布仍由现有 `onRun()` 二次确认和 preflight 控制。
