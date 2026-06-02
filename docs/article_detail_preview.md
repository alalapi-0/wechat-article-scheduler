# 文章详情与预览（Round 66 / 收敛 Round 11）

## 路由

| 路径 | 说明 |
|------|------|
| `GET /articles/{id}` | 桌面优先详情页（普通视图 + 高级开关） |
| `GET /api/articles/{id}` | 详情 JSON：排期、草稿、预检、下一步 |
| `GET /api/articles/{id}/render-preview` | 公众号正文 HTML 预览 |

工作台作品卡片提供 **详情** 链接；弹窗预览仍保留。

## 普通视图展示

- 标题、合集、状态与下一步建议
- 发布任务计划时间、草稿状态（mock 模式有演练说明）
- 发布前检查：封面、摘要长度、正文质量
- 摘要预览、封面图、正文 HTML 预览

## 验证

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli serve
# 浏览器打开 http://127.0.0.1:8080/articles/<id>
python -m pytest tests/test_article_detail_page.py -q
```
