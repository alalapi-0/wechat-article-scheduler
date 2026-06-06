# 浏览器测试

涉及页面、审核台、预览、发布流程或文件操作的任务，必须验证真实页面，不能只看代码或截图。

## 标准流程

1. 默认以 `WECHAT_MODE=mock` 启动本地服务。
2. 用 Playwright 或 chrome-devtools 打开 `http://127.0.0.1:8080/`。
3. 走至少一条核心用户路径。
4. 检查 loading、empty、success、warning、error。
5. 检查 console 无未处理 error。
6. 检查核心 network 请求无意外 4xx/5xx。
7. 主验收 `1280x900`；兼容 `768` 和 `375` 宽度。
8. 运行相关 pytest 和 Agent gate。

```bash
python3 -m wechat_article_scheduler.cli serve
python3 -m pytest tests/test_ui_e2e.py tests/test_ui_review.py -q
python3 scripts/agent_gate.py gate
```

Stitch screenshot 只用于比较设计意图；页面成功必须由运行中的 DOM、交互、console、network 和测试共同证明。
