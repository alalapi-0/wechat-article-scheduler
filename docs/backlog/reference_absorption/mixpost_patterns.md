# Mixpost 模式吸收

## 可吸收模式

- `PostVersion`：平台变体和主内容分离。
- `PostAccount`：平台账号是独立实体，不把账号配置写死在平台名上。
- `SocialProviderPostConfigs`：平台限制和 payload 配置化。
- 状态与调度分离：业务发布结果和队列执行状态分别建模。

## 本项目落点

- `canonical_text` 保存主内容。
- `platform_payload` 保存微信公众号、知乎、豆瓣、B站、小红书等平台变体。
- `platform_account` 记录账号、安全模式、凭证引用。
- `platform_profile` 记录平台能力和约束。
- dry-run 根据平台 profile 校验 payload。

## 不吸收

- 不嵌入 Mixpost。
- 不引入 Laravel 包生态。
- 不照搬其 UI、队列系统和数据库结构。
- 不在本轮实现多账号发布。
