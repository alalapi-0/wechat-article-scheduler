# wechat-article-scheduler

本地优先的微信公众号图文 **收件箱 → 排期 → mock 草稿/发布** CLI。默认不调用真实微信 API。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/rules.example.yaml config/rules.yaml
python -m wechat_article_scheduler.cli init-db
```

将 `.md` / `.txt` / `.html` 放入 `articles/inbox/`，然后：

```bash
python -m wechat_article_scheduler.cli scan
python -m wechat_article_scheduler.cli plan
python -m wechat_article_scheduler.cli run-once
```

## 命令

| 命令 | 说明 |
|------|------|
| `init-db` | 初始化 SQLite |
| `scan` | 扫描 inbox、去重、入库 |
| `plan` | 生成 `publish_jobs` |
| `run-once` | 执行到期任务（mock 草稿） |
| `scheduler` | 后台轮询 |
| `reject --article-id N` | 驳回 (Round 1) |
| `retry-failed` | 重试失败任务 (Round 1) |
| `events --limit N` | 审计事件 (Round 2) |

## 配置

- `.env`：见 `.env.example`（勿提交）
- `config/rules.yaml`：去重与排期规则

## 治理

见 `governance/`、`docs/rounds.md`、`scripts/agent_gate.py`。

## 安全

- 仓库内无真实密钥
- 不使用 Cookie 爬取
- 日志不输出 token
