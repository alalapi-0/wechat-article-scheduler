"""Phase 3 视频内容包预研 dry-run（Round 29 / round_090，不上传）。"""

from __future__ import annotations

from typing import Any

VIDEO_GUARDRAILS: list[str] = [
    "不上传视频文件到任何平台",
    "不调用 Bilibili/视频号/小红书上传 API",
    "视频路径仅作本地引用，dry-run 不读取二进制",
    "发布成功必须以人工 proof 为准",
    "不影响微信公众号文章 scan/plan 主线",
    "大文件转码与版权审核由用户自行处理",
]

VIDEO_PACKAGE_FIELDS: list[dict[str, str]] = [
    {"field_id": "video_path", "label": "主视频", "required": True},
    {"field_id": "cover_path", "label": "封面", "required": True},
    {"field_id": "title", "label": "标题", "required": True},
    {"field_id": "description", "label": "简介", "required": False},
    {"field_id": "tags", "label": "标签", "required": False},
    {"field_id": "subtitle_path", "label": "字幕", "required": False},
    {"field_id": "chapter_markers", "label": "章节点", "required": False},
]

PLATFORM_PRESEARCH: dict[str, dict[str, Any]] = {
    "bilibili": {
        "label": "Bilibili",
        "adapter_types": ["manual_export", "browser_assist"],
        "risk_level": "high",
        "recommendation": "manual_export_first",
        "summary": "优先人工上传包；browser_assist 仅评估，不适合无人值守。",
    },
    "wechat_channels": {
        "label": "微信视频号",
        "adapter_types": ["manual_export"],
        "risk_level": "high",
        "recommendation": "deferred",
        "summary": "与公众号 API 分离；仅预研导出字段，不假装 API 已支持。",
    },
    "xiaohongshu": {
        "label": "小红书视频",
        "adapter_types": ["manual_export"],
        "risk_level": "high",
        "recommendation": "deferred",
        "summary": "高风控；Phase3 仅字段清单与 outbox 设想。",
    },
}


def build_video_package_dry_run(
    *,
    platform: str = "bilibili",
    package_id: str | None = None,
    title: str | None = None,
    video_path: str | None = None,
) -> dict[str, Any]:
    """视频内容包评估干跑（不触碰文件、不上传）。"""
    key = (platform or "bilibili").strip().lower()
    meta = PLATFORM_PRESEARCH.get(key)
    if meta is None:
        raise ValueError(
            f"不支持的视频预研平台：{platform}；可选：{', '.join(PLATFORM_PRESEARCH)}"
        )
    return {
        "mode": "dry_run",
        "phase": "phase3_presearch",
        "content_type": "video",
        "platform": key,
        "status": "evaluation_only",
        "terminal_policy": "不得自动标记视频已发布",
        "package_id": package_id or "sample-video-001",
        "title": title or "示例视频内容包",
        "video_path_hint": video_path or "media/sample.mp4",
        "guardrails": VIDEO_GUARDRAILS,
        "package_fields": list(VIDEO_PACKAGE_FIELDS),
        "platform_assessment": {
            "label": meta["label"],
            "adapter_types": meta["adapter_types"],
            "risk_level": meta["risk_level"],
            "recommendation": meta["recommendation"],
            "summary": meta["summary"],
        },
        "registry_placeholders": [
            {"platform": key, "adapter_type": at, "implemented": False}
            for at in meta["adapter_types"]
        ],
        "outbox_artifacts_planned": [
            "video_path.txt",
            "cover.*",
            "title.txt",
            "description.txt",
            "tags_hint.md",
            "upload_checklist.md",
        ],
        "note": "预研占位；articles 表与 scan/plan 仍仅服务图文文章。",
    }


def list_video_platforms() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "recommendation": v["recommendation"]}
        for k, v in PLATFORM_PRESEARCH.items()
    ]
