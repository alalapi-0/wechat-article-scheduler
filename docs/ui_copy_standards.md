# UI 文案标准（Round 20）

## 单一来源

所有普通视图中文文案来自 `src/wechat_article_scheduler/web/user_copy.py`。  
Web 页面通过 `/api/user-labels` 加载映射；新增状态或按钮时先更新该模块。

## 原则

1. 普通视图用**完整中文句子**，不用裸英文枚举。
2. 内部字段名（如 `imported`）仅允许出现在高级/调试区，且须标注「调试用」。
3. 同一状态全局只有一种叫法（见 `ARTICLE_STATUS` / `JOB_STATUS`）。
4. 模式说明必须回答「会不会真的发到公众号」。

## 禁止出现在普通视图的词

见 `FORBIDDEN_ORDINARY_TERMS`：`publish_jobs`、`payload_json`、`mock`、`pending` 等。

## 按钮与步骤

| 内部 action | 普通用户说法 |
|---|---|
| scan | 扫描收件箱 |
| plan | 安排发布时间 |
| run-once | 执行到点文章 |
| status | 刷新状态 |

主流程三步见 `STEP_LABELS`。

## 测试

`tests/test_web_ordinary_copy.py` 校验文案模块与首页 HTML 不含禁止词。
