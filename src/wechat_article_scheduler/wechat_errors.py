"""微信公众号 API 常见错误码可读说明（Round 58 / 收敛 Round 3）。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.wechat_http import WechatApiError

# 摘自公众号开发文档常见 errcode；未列出的仍返回原始 errmsg
COMMON_ERROR_HINTS: dict[int, str] = {
    40001: "access_token 无效或过期，请检查凭证或稍后重试",
    40003: "AppID 无效，请核对 WECHAT_APP_ID",
    40013: "AppSecret 无效，请核对 WECHAT_APP_SECRET",
    40007: "子菜单或素材相关权限不足",
    40125: "无效的 appsecret",
    41001: "缺少 access_token 参数",
    42001: "access_token 超时，将自动刷新后重试",
    43004: "需要接收者关注公众号（部分接口）",
    45009: "接口调用超过限制，请稍后重试",
    45047: "客服接口下行条数超过上限",
    48001: "当前 API 未授权，请确认公众号类型与接口权限",
    50002: "用户受限，可能是违规或接口封禁",
    61451: "草稿数据非法，请检查标题/摘要/正文",
    61452: "草稿不存在",
    61453: "草稿已删除",
    85019: "草稿数量已达上限，请清理公众号后台草稿",
}


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
