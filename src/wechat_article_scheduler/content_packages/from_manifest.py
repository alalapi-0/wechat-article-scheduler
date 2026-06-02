"""Build content_package drafts from a validated publish manifest."""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.adapters.registry import (
    infer_platform_from_account_id,
    is_known_adapter,
)
from wechat_article_scheduler.core.manifest_loader import validate_manifest
from wechat_article_scheduler.core.models import ContentPackageDraft, PlatformPayloadDraft


def manifest_to_drafts(
    manifest: dict[str, Any],
) -> tuple[ContentPackageDraft, list[PlatformPayloadDraft], list[str]]:
    """
    Convert manifest dict to package + payload drafts.

    Returns (package, payloads, warnings). Raises ValueError if validation fails.
    """
    result = validate_manifest(manifest)
    if not result.ok:
        raise ValueError("; ".join(result.errors))

    warnings = list(result.warnings)
    package = ContentPackageDraft(
        project_id=str(manifest["project_id"]),
        package_id=str(manifest["package_id"]),
        title=str(manifest["title"]),
        content_type=str(manifest.get("content_type") or "article"),
        summary=str(manifest.get("summary") or ""),
        metadata={
            "body_md": manifest.get("body_md"),
            "body_html": manifest.get("body_html"),
            "media_refs": manifest.get("media_refs") or [],
        },
    )

    payloads: list[PlatformPayloadDraft] = []
    for target in manifest.get("targets") or []:
        account_id = str(target["platform_account_id"])
        adapter_type = str(target["adapter_type"])
        platform = infer_platform_from_account_id(account_id)
        if platform and not is_known_adapter(platform, adapter_type):
            warnings.append(
                f"未在 registry 声明: {platform}+{adapter_type} ({account_id})"
            )
        payloads.append(
            PlatformPayloadDraft(
                content_package_id=f"{package.project_id}:{package.package_id}",
                platform_account_id=account_id,
                title=package.title,
                content_type=package.content_type,
                extra={
                    "adapter_type": adapter_type,
                    "platform": platform,
                    "scheduled_at": target.get("scheduled_at"),
                    "review_required": bool(target.get("review_required")),
                    "target_extra": target.get("extra") or {},
                },
            )
        )

    return package, payloads, warnings


def manifest_dry_run_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Dry-run import preview without touching SQLite."""
    package, payloads, warnings = manifest_to_drafts(manifest)
    validation = validate_manifest(manifest)
    registry_checks = []
    for p in payloads:
        platform = p.extra.get("platform")
        adapter_type = p.extra.get("adapter_type")
        registered = bool(
            platform and adapter_type and is_known_adapter(platform, adapter_type)
        )
        registry_checks.append(
            {
                "platform_account_id": p.platform_account_id,
                "platform": platform,
                "adapter_type": adapter_type,
                "registered": registered,
            }
        )
    return {
        "ok": True,
        "validation": validation.to_dict(),
        "content_package": {
            "project_id": package.project_id,
            "package_id": package.package_id,
            "title": package.title,
            "content_type": package.content_type,
            "summary": package.summary,
        },
        "target_count": len(payloads),
        "targets": [
            {
                "platform_account_id": p.platform_account_id,
                "adapter_type": p.extra.get("adapter_type"),
                "platform": p.extra.get("platform"),
                "scheduled_at": p.extra.get("scheduled_at"),
                "review_required": p.extra.get("review_required"),
            }
            for p in payloads
        ],
        "registry_checks": registry_checks,
        "warnings": warnings,
        "note": "dry-run only；未写入数据库，scan/plan 仍为微信主线。",
    }
