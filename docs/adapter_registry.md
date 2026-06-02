# Adapter Registry

Status: 实验性能力声明（round_085+）

`wechat_article_scheduler.adapters.registry` 列出当前支持的 `platform + adapter_type` 组合，供 manifest 干跑、Web `/debug` 与 API 查询。**不**替代 `adapters/__init__.py` 中的微信公众号运行时适配器选择。

## 内置能力

| platform | adapter_type | 说明 |
|----------|--------------|------|
| wechat_mp | official_api | 微信官方 API（mock/real） |
| wechat_mp | browser_assist | API 缺口人工辅助 dry-run |
| zhihu | manual_export | outbox 导出 |
| zhihu | browser_assist | 评估 dry-run |
| douban | manual_export | outbox 导出 |
| douban | browser_assist | 评估 dry-run |
| generic | manual_export | 通用导出 |

## CLI / API

- `python -m wechat_article_scheduler.cli adapter-registry`
- `GET /api/adapter-registry`
