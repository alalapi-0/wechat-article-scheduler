"""微信公众号后台固定字段能力模型（Round 134）。"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

CapabilityLevel = Literal["api_supported", "browser_required", "unavailable"]


class BackendFieldCapability(TypedDict):
    field_id: str
    label: str
    level: CapabilityLevel
    note: str


BACKEND_FIELD_CAPABILITIES: list[BackendFieldCapability] = [
    {
        "field_id": "fixed_collection",
        "label": "固定合集",
        "level": "browser_required",
        "note": "微信 API 草稿接口不直接写入合集；需后台或外部 Agent 人工设置",
    },
    {
        "field_id": "need_open_comment",
        "label": "留言",
        "level": "api_supported",
        "note": "draft/add 与 publish_config 已接线",
    },
    {
        "field_id": "only_fans_can_comment",
        "label": "仅粉丝留言",
        "level": "api_supported",
        "note": "依赖开启留言",
    },
    {
        "field_id": "recommend_notify",
        "label": "推荐/通知",
        "level": "unavailable",
        "note": "当前 API 未映射；仅任务目标记录，需后台人工",
    },
    {
        "field_id": "show_cover_pic",
        "label": "封面显示",
        "level": "browser_required",
        "note": "show_cover_pic 等待官方字段核验；默认走后台核对",
    },
    {
        "field_id": "wechat_backend_schedule",
        "label": "后台定时",
        "level": "unavailable",
        "note": "本地 scheduler 到点执行；不能写入微信后台定时字段",
    },
]


def list_backend_field_capabilities() -> list[dict[str, Any]]:
    return [dict(row) for row in BACKEND_FIELD_CAPABILITIES]


def field_level(field_id: str) -> CapabilityLevel:
    for row in BACKEND_FIELD_CAPABILITIES:
        if row["field_id"] == field_id:
            return row["level"]
    return "unavailable"
