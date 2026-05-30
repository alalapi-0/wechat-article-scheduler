# AGENTS.md

微信公众号文章本地调度器。默认 **WECHAT_MODE=mock**，不调用真实微信 API。

## 阅读顺序

1. `governance/repo_protocol_standard.yaml`
2. `project.yaml`
3. `governance/agent_policy.yaml`
4. `governance/round_state.yaml`
5. `docs/rounds.md`
6. `README.md`

## 自主推进

```bash
python scripts/agent_gate.py
```

门控会运行 `pytest`、当前轮冒烟测试；通过后在 Git 上提交并更新 `governance/round_state.yaml`。

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
