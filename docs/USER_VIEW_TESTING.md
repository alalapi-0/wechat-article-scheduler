# User View Testing

项目类型：**Web/UI 工作台 + 发布工具（草稿-only）**

## 测试重点

### Web 工作台

1. 启动：`python -m wechat_article_scheduler.cli serve`
2. 打开 `http://127.0.0.1:8080/`
3. 主流程：上传 → 扫描 → 排期 → 队列 → 预检 → 事件日志
4. 空状态 / 错误状态 / 按钮文案
5. Desktop-first（1280px）；兼容 375px / 768px
6. console error、network error
7. 截图存档至 `docs/reports/ui_review/`

### 发布工具（草稿）

- dry-run：`python -m wechat_article_scheduler.cli plan`
- mock 草稿创建
- **不真实发布**
- 外部任务包：`export-agent-task`
- 平台限制见 `docs/wechat_capability_matrix.md`

### AI/流水线（轻量）

- 章节导入完整性（`articles/imported/`）
- 输出格式与 digest 120 字
- 成本：默认 mock，无 LLM 调用

## 脚本

```bash
# 结构检查（默认安全）
python scripts/user_view_test.py --dry-run

# 含 pytest 子集（需环境）
python scripts/user_view_test.py --pytest

# pytest 用户视角
python -m pytest tests/test_user_view_rounds_abcd.py -q
python -m pytest tests/test_ui_e2e.py -q
```

## MCP 用户视角

优先 **playwright** 或 **chrome-devtools**（本地 UI）。  
微信公众号已登录后台 → **wechat-chrome-session** only。

## 报告

- `docs/reports/ux_loop/UX-LOOP-*_user_view_test_report.md`
- `scripts/user_view_test.py` 输出 JSON 至同目录
