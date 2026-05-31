# Autonomous Real API Round 2 Report

## 本轮目标

在真实 API 报告中加入渲染预览与质量备注；校准预检「真实草稿」文案；复跑 1 条样本验证调优。

## 使用的真实 API / 模型

- Provider: 微信公众平台
- 调用次数: 1（`--samples 1`）
- 是否使用 mock: **No**

## 真实生成输出

- 报告: `reports/real_api_runs/run_20260531T230611Z.*`
- 成功: 1 / 失败: 0
- `rendered_preview` 含双段落 `<p>` 样式，长度 206 字符

## 质量观察

- 样本 `03_escaped_html` 经 `render_for_publish` 后 **无** `&lt;` 残留（unescape 正常）
- `real_api_check` 现区分「已归一化」与「仍含转义」两类备注

## 本轮调优

- `real_api_check`: `rendered_len` / `rendered_preview` / 转义质量备注
- `publish_preflight`: 真实草稿模式说明更清晰
- UI: `#safetyTop` 浏览器验证为「真实连接 · 仅创建草稿，不会发布」

## 验证命令

- `pytest tests/test_web_round39_plus.py tests/test_publish_preview.py tests/test_real_api_check.py` → 17 passed
- `real_api_check --samples 1` → exit 0
- 浏览器: `http://127.0.0.1:8080/` API status `real` + publish false

## 是否自动进入下一轮

**是，继续 Round 3**
