# 真实 API 测试

项目默认 `WECHAT_MODE=mock`。真实 API 测试必须显式设置 `WECHAT_MODE=real`，推荐同时设置 `WECHAT_ENABLE_PUBLISH=false`，只验证 token、素材和草稿，不提交正式发布。

## 原则

- 无凭证时使用 mock 或 dry-run，并明确标记；不得把 mock 冒充 real_api。
- 不读取、打印或提交 `.env`、AppSecret、access token、cookie。
- 真实请求前确认账号权限、样本数量和副作用。
- 报告只保存脱敏摘要、状态、错误码和下一步，不保存凭证。
- 当前账号发布接口无权限时，真实链路停在草稿与人工/外部 Agent 确认。

```bash
python3 scripts/real_api_check.py --dry-run --skip-if-blocked
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false \
  python3 scripts/real_api_check.py --samples 3
```

只有用户明确授权并确认账号能力时，才测试带正式发布副作用的路径。
