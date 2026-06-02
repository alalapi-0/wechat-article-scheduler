"""抖音/快手短视频平台 deferred 评估 dry-run（round_099）。"""

from __future__ import annotations

from typing import Any

SHORT_VIDEO_GUARDRAILS: list[str] = [
    "不上传视频、不登录抖音/快手",
    "不保存 cookie 或设备指纹",
    "deferred：默认不进入自动发布路线",
    "人工 proof 前不得标为已发布",
    "不影响微信公众号 scan/plan 主线",
]

PLATFORM_META: dict[str, dict[str, Any]] = {
    "douyin": {
        "label": "抖音",
        "risk_level": "high",
        "recommendation": "deferred",
        "summary": "高风控短视频平台；仅 manual_export 包 + 人工上传，暂缓 browser_assist 自动化。",
        "export_cli": "export-outbox --platform douyin",
    },
    "kuaishou": {
        "label": "快手",
        "risk_level": "high",
        "recommendation": "deferred",
        "summary": "高风控；与抖音同属 deferred 预研，仅导出骨架与清单。",
        "export_cli": "export-outbox --platform kuaishou",
    },
}


def build_short_video_deferred_plan(
    *,
    platform: str = "douyin",
    article_id: str | None = None,
) -> dict[str, Any]:
    key = (platform or "douyin").strip().lower()
    if key == "ks":
        key = "kuaishou"
    meta = PLATFORM_META.get(key)
    if meta is None:
        raise ValueError(
            f"不支持的平台：{platform}；可选：{', '.join(PLATFORM_META)}"
        )
    return {
        "mode": "dry_run",
        "phase": "phase3_deferred",
        "platform": key,
        "status": "deferred_evaluation",
        "article_id": article_id,
        "guardrails": SHORT_VIDEO_GUARDRAILS,
        "assessment": {
            "risk_level": meta["risk_level"],
            "recommendation": meta["recommendation"],
            "summary": meta["summary"],
            "blockers": ["反自动化与营销合规", "视频需用户自备"],
            "fallback": meta["export_cli"],
        },
        "note": "预研评估 only；不实现 adapter 真上传。",
    }


def list_short_video_platforms() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "recommendation": v["recommendation"]}
        for k, v in PLATFORM_META.items()
    ]
