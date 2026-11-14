"""微信公众号 API 常见错误码可读说明。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.wechat_http import WechatApiError

# 摘自公众号开发文档常见 errcode；未列出的仍返回原始 errmsg
COMMON_ERROR_HINTS: dict[int, str] = {
    40001: "access_token 无效或过期，请检查凭证或稍后重试",
    40003: "AppID 无效，请核对 WECHAT_APP_ID",
    40013: "AppID 无效，请核对 WECHAT_APP_ID",
    40007: "子菜单或素材相关权限不足",
    40014: "access_token 不合法，请核对令牌来源",
    40125: "AppSecret 不合法，请由用户在本地核对凭据",
    40164: "出口 IP 不在白名单，请由用户核对公众号后台 IP 白名单",
    40243: "AppSecret 已冻结，请由用户在公众号后台处理",
    41001: "缺少 access_token 参数",
    42001: "access_token 超时；当前请求未自动刷新重试，请核对令牌后人工决定是否重试",
    43004: "需要接收者关注公众号（部分接口）",
    45009: "接口调用超过限制，请稍后重试",
    45011: "接口调用频率超过限制，请稍后重试",
    45047: "客服接口下行条数超过上限",
    48001: "当前 API 未授权，请确认公众号类型与接口权限",
    50002: "用户受限，可能是违规或接口封禁",
    61451: "草稿数据非法，请检查标题/摘要/正文",
    61452: "草稿不存在",
    61453: "草稿已删除",
    85019: "草稿数量已达上限，请清理公众号后台草稿",
}


def wechat_error_diagnostic(errcode: int) -> dict[str, str]:
    """返回安全的原因和处理提示；不回显 API 原始 errmsg 或请求 URL。"""
    code = int(errcode)
    if code == 48001:
        reason = "endpoint_unauthorized"
    elif code == 40164:
        reason = "ip_whitelist"
    elif code == 40243:
        reason = "appsecret_frozen"
    elif code == 40125:
        reason = "invalid_appsecret"
    elif code == 40013:
        reason = "invalid_appid"
    elif code in {40001, 40014, 41001, 42001}:
        reason = "token_error"
    elif code in {45009, 45011, 45047}:
        reason = "rate_limited"
    else:
        reason = "api_error"
    message = COMMON_ERROR_HINTS.get(code, f"微信 API 错误 {code}")
    return {"reason_code": reason, "message": message, "action_hint": message}


def human_wechat_error(errcode: int, errmsg: str = "") -> str:
    """返回面向用户的简短说明（不含 secret）。"""
    hint = COMMON_ERROR_HINTS.get(int(errcode))
    if hint:
        return hint
    if errmsg:
        return f"微信 API 错误 {errcode}：{errmsg}"
    return f"微信 API 错误 {errcode}"


def format_job_failure(exc: BaseException) -> str:
    """写入 events.job_failed 的安全载荷（截断）。"""
    if isinstance(exc, WechatApiError):
        text = human_wechat_error(exc.errcode, exc.errmsg)
        return f"{text} [{exc.endpoint}]"[:500]
    return str(exc)[:500]
