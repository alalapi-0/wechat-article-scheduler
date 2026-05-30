# 普通用户工作台原则（Round 19 验收地基）

> 目标读者：完全不懂编程的个人用户。  
> 使用场景：**电脑浏览器**中的本地工作台（Desktop-first local workbench）。  
> 本文件是 Phase 6–8（Round 19–38）的验收权威；机器门控见 `scripts/agent_gate.py` 与 `tests/test_ui_review.py`。

## 四个核心问题

普通视图默认只回答：

1. **现在安全吗** — 会不会真的发到公众号？
2. **下一步做什么** — 按清晰步骤完成找文章、排时间、执行到点文章。
3. **刚才做成了吗** — 用人话说明本次操作结果。
4. **出错了怎么办** — 给出原因、影响和下一步，而不是堆内部字段。

## 桌面优先

- 主验收视口：**1280×900** 桌面浏览器。
- 窄屏（768 / 375）只做**兼容验收**：无整页横向溢出、关键按钮可点、文字可读。
- 不为手机卡片化牺牲桌面信息密度与表格扫读效率。

## 三层信息边界

| 层级 | 目的 | 默认可见 | 示例 |
|---|---|---|---|
| 普通视图 | 非技术用户日常操作 | 是 | 「当前是演练，不会真的发到公众号」 |
| 详情视图 | 追踪单篇文章或任务 | 点击后 | 标题、计划时间、失败原因 |
| 高级/调试视图 | Agent/开发者排错 | 否，需开关 | 数据库路径、原始 JSON、内部 id |

详细字段清单见 [`docs/info_layer_boundary.md`](info_layer_boundary.md)。

## 普通视图禁止项（基线）

以下不得出现在普通视图首屏（Round 21+ 实现时逐项落地）：

- 数据库绝对路径
- 原始 JSON / `payload_json`
- 裸英文内部枚举（如 `imported`、`pending`、`mock`）
- 内部表名（如 `publish_jobs`）
- 内部统计字段名（如 `processed`、`skipped_future`）

## 诊断与截图基线

- 诊断脚本：`tools/browser_automation/ui_review.py`
- 有数据基线：`docs/reports/ui_review/seeded/`（桌面 / 平板 / 手机三视口）
- 空状态基线：`docs/reports/ui_review/empty_state/`
- 结构快照：各子目录下的 `dom_snapshot.md`
- 人话诊断报告：`docs/web_console_usability_review.md`

### 复跑命令

```bash
# 安装（一次性）
pip install -e ".[dev]" && playwright install chromium

# 有数据桌面基线（默认 5 篇样稿）
WECHAT_MODE=mock .venv/bin/python tools/browser_automation/ui_review.py --seed 5

# 空状态基线
WECHAT_MODE=mock .venv/bin/python tools/browser_automation/ui_review.py --seed 0

# CI / 无浏览器环境：见 tests/test_ui_review.py（结构校验 + 可选 headless 截图）
.venv/bin/python -m pytest tests/test_ui_review.py -q
```

## 与后续轮次关系

- Round 20–25：普通视图文案、信息减法、主流程、反馈、空状态、安全护栏
- Round 26–30：桌面布局与列表/队列/事件普通化、高级信息开关
- Round 35：Playwright E2E 断言固化
- Round 38：后续功能接入须先声明三层字段归属
