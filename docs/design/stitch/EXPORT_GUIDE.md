# Stitch 导出规范

## 保存位置

| 产物 | 目录 |
|---|---|
| 实际 prompt | `docs/design/stitch/prompts/` |
| HTML、DESIGN.md、结构化说明 | `docs/design/stitch/exports/` |
| screen、variant 截图 | `docs/design/stitch/screenshots/` |
| 评审、任务拆分、验收记录 | `docs/design/stitch/reviews/` |

建议文件名：`YYYYMMDD-页面名-v01.ext`。同一设计的 prompt、HTML、截图和 review 使用相同前缀。

## 导出步骤

1. 记录 Stitch project id、screen id 和生成日期，不记录 key。
2. 通过 Stitch tool 获取 screen 元数据。
3. 下载 `htmlCode.downloadUrl` 对应 HTML 到 `exports/`。
4. 下载 `screenshot.downloadUrl` 对应图片到 `screenshots/`。
5. 将设计 token、布局、组件、状态和响应式决策整理成 `exports/*-DESIGN.md`。
6. 在 `reviews/` 记录采用项、拒绝项和实现任务。

下载 URL 可能是临时地址，不应把带签名或 token 的 URL写入仓库。只保存最终文件和不敏感的 project/screen 标识。

## 评审门槛

导出 HTML 不能直接替换项目代码。评审必须检查：

- 是否符合普通用户优先和桌面优先；
- 是否暴露内部字段或误导真实发布能力；
- 是否引入 React/Vue、远端字体、分析脚本或未知依赖；
- 是否包含真实 key、token、cookie、下载签名；
- 是否覆盖完整交互状态和错误恢复；
- 如何映射到现有 FastAPI 页面、服务和测试。

实现完成后，Stitch screenshot 只能作为视觉参考；成功结论必须来自真实浏览器、console、network 和自动化测试。
