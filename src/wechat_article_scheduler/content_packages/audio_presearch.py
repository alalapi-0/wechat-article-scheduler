"""Phase 4 音频/播客内容包预研 dry-run（Round 36+ / round_100）。"""

from __future__ import annotations

from typing import Any

AUDIO_GUARDRAILS: list[str] = [
    "不上传音频到任何平台",
    "不调用网易云/播客托管 API",
    "版权与授权须用户自行确认并记录",
    "dry-run 不读取音频二进制",
    "不影响微信公众号文章主线",
    "podcast RSS 仅作字段预研，不自动推送",
]

AUDIO_PACKAGE_FIELDS: list[dict[str, str]] = [
    {"field_id": "audio_path", "label": "主音频", "required": True},
    {"field_id": "cover_path", "label": "封面", "required": True},
    {"field_id": "title", "label": "节目标题", "required": True},
    {"field_id": "summary", "label": "节目说明", "required": False},
    {"field_id": "lyrics_path", "label": "歌词/LRC", "required": False},
    {"field_id": "show_notes_md", "label": "Show Notes", "required": False},
    {"field_id": "copyright_notice", "label": "版权说明", "required": False},
    {"field_id": "rss_feed_url", "label": "RSS（播客）", "required": False},
]

PLATFORM_META: dict[str, dict[str, Any]] = {
    "podcast": {
        "label": "播客 RSS",
        "content_type": "podcast",
        "risk_level": "medium",
        "recommendation": "conditional",
        "summary": "适合自有 RSS 托管；需版权清晰与 show notes。",
    },
    "audio": {
        "label": "通用音频内容包",
        "content_type": "audio",
        "risk_level": "low",
        "recommendation": "recommended",
        "summary": "本地音频+封面+说明的通用抽象，不绑定单一平台。",
    },
    "netease_music": {
        "label": "网易云音乐",
        "content_type": "music",
        "risk_level": "high",
        "recommendation": "deferred",
        "summary": "版权与审核复杂；仅 registry 占位，不实现上传。",
    },
}


def build_audio_package_dry_run(
    *,
    platform: str = "podcast",
    package_id: str | None = None,
    title: str | None = None,
    audio_path: str | None = None,
) -> dict[str, Any]:
    key = (platform or "podcast").strip().lower()
    if key in ("netease", "netease_music"):
        key = "netease_music"
    meta = PLATFORM_META.get(key)
    if meta is None:
        raise ValueError(
            f"不支持的音频预研平台：{platform}；可选：{', '.join(PLATFORM_META)}"
        )
    return {
        "mode": "dry_run",
        "phase": "phase4_presearch",
        "content_type": meta["content_type"],
        "platform": key,
        "status": "evaluation_only",
        "terminal_policy": "不得自动标记音频已发行",
        "package_id": package_id or "sample-audio-001",
        "title": title or "示例音频节目",
        "audio_path_hint": audio_path or "media/episode.mp3",
        "guardrails": AUDIO_GUARDRAILS,
        "package_fields": list(AUDIO_PACKAGE_FIELDS),
        "platform_assessment": {
            "label": meta["label"],
            "risk_level": meta["risk_level"],
            "recommendation": meta["recommendation"],
            "summary": meta["summary"],
        },
        "registry_placeholders": [
            {"platform": key, "adapter_type": "manual_export", "implemented": False},
        ],
        "manifest_hints": {
            "podcast": "manifests/examples/sample_podcast_manifest.json",
            "audio": "manifests/examples/sample_audio_manifest.json",
        },
        "note": "预研 only；articles 表仍仅服务图文。",
    }


def list_audio_platforms() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "recommendation": v["recommendation"]}
        for k, v in PLATFORM_META.items()
    ]
