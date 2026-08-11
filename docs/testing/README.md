# 测试

## 本地测试

完整测试：

    .venv/bin/python -m pytest -q

结构和安全契约：

    .venv/bin/python scripts/check_repo_contract.py

改动时先运行受影响模块，再运行全量。当前没有单独 lint、format 或静态类型检查配置，不应虚构命令。

## Web E2E

    .venv/bin/python -m pytest tests/test_ui_e2e.py -q

Playwright/Chromium 不可用时测试会按代码条件跳过。UI 改动若浏览器可用，还应打开真实 localhost 页面，走核心用户路径并检查 console、network 和响应式布局。

所有测试数据库、inbox、outbox、截图和 DOM 快照必须写入 tmp_path 或系统临时目录。测试后 git status 不应新增运行产物。

## real API

默认不做真实 API 验收。无网络 dry-run：

    .venv/bin/python scripts/real_api_check.py --dry-run --skip-if-blocked

只有用户明确授权且本地环境已安全配置时，才运行会创建真实草稿的检查：

    WECHAT_MODE=real .venv/bin/python scripts/real_api_check.py --samples 3

不得输出 .env、AppSecret、token 或 cookie。检查不调用最终发布接口。真实报告写入被 Git 忽略的 reports/real_api_runs/。
