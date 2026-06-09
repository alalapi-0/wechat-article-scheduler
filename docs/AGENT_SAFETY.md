# Agent Safety

## 默认禁止

- 读取/打印 `.env`、cookie、token、私钥
- 默认 `WECHAT_MODE=real` 联网
- 真实发布、群发、确认定时发布
- `git push --force` 到 main
- 提交大文件、浏览器 session、真实用户数据
- 为通过 gate 删除失败测试

## 默认允许（只读/安全）

- `git status` / `git diff`
- `pytest`（mock 模式）
- `npm run check:mcp`
- `python scripts/tool_probe.py`
- Web 搜索官方文档
- 本地 `serve` 在 127.0.0.1

## 需显式授权

- `git commit`
- `git push`
- `WECHAT_MODE=real`
- 修改已发布公众号内容
- 删除 `articles/` 文稿

## P0 定义

数据丢失、密钥泄露、应用无法启动、构建完全损坏、破坏性操作、真实发布/API 误触发。

## P0/P1 未清零

不做 P2/P3 优化。
