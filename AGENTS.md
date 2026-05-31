# AGENTS.md

微信公众号文章本地调度器。默认 **WECHAT_MODE=mock**，不调用真实微信 API。

## 路线图单一真相来源

| 用途 | 文件 |
|------|------|
| 人类可读路线图（权威） | `docs/rounds.md`（Round 0–53） |
| 机器可读轮次注册表 | `scripts/agent_gate.py` 的 `ROUND_ORDER` / `ROUND_META` |
| 当前轮次运行状态 | `governance/round_state.yaml` |

修改路线图时：**先改 `docs/rounds.md`，再同步 `agent_gate.py` 与 `tests/test_agent_gate.py`**。`articles/imported/` 与 `articles/published/` 下的章节文稿已纳入仓库，供 scan/plan 测试使用。

Web 控制台路线图原则：**普通用户视图优先 + Desktop-first local workbench**。普通视图只回答“现在安全吗、下一步做什么、刚才做成了吗、出错了怎么办”；数据库路径、原始 JSON、内部字段、调试统计默认进入高级信息开关。优先电脑浏览器的信息密度、任务队列表格、文章列表、事件日志、左侧导航/顶部状态；手机/平板只做响应式兼容（不横向溢出、关键按钮可点、页面可读），不得作为默认布局目标。

## 阅读顺序

1. `governance/repo_protocol_standard.yaml`
2. `project.yaml`
3. `governance/agent_policy.yaml`
4. `governance/round_state.yaml`
5. `docs/rounds.md`
6. `README.md`

## 自主推进

```bash
python scripts/agent_gate.py status          # 当前轮、验收项、next_actions
python scripts/agent_gate.py gate            # pytest + 轮次冒烟（exit 0 可继续）
python scripts/agent_gate.py advance --commit  # 通过后推进 round_state；可选提交
```

Agent 循环：`status` → 实现任务 → `gate` → `advance --commit`。默认**不** push；`--check-only` 等价于 `gate`。退出码：0=PASS，1=WARNING，2=BLOCKED（见 `governance/repo_protocol_standard.yaml`）。

## 禁止

- 读取/打印 `.env` 密钥
- 日志打印 token
- 未授权时 `WECHAT_MODE=real` 联网

## 常用命令

```bash
python -m wechat_article_scheduler.cli init-db
python -m wechat_article_scheduler.cli scan
python -m wechat_article_scheduler.cli plan
python -m wechat_article_scheduler.cli run-once
python -m pytest
```
