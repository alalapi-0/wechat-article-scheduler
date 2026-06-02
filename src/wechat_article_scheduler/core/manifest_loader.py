"""publish_manifest.json load and validate (no DB import)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ManifestValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a publish_manifest.json without importing it into the DB."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data: dict[str, Any]) -> ManifestValidationResult:
    """Validate manifest shape per docs/backlog/multi_project_manifest_design.md."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ManifestValidationResult(ok=False, errors=["manifest 必须是 JSON 对象"])

    version = data.get("schema_version")
    if version is None:
        errors.append("缺少 schema_version")
    elif version != 1:
        errors.append(f"不支持的 schema_version: {version!r}（当前仅支持 1）")

    for key in ("project_id", "package_id", "title"):
        val = data.get(key)
        if not val or not str(val).strip():
            errors.append(f"缺少或为空: {key}")

    content_type = data.get("content_type")
    if not content_type:
        warnings.append("未设置 content_type，将按 article 处理")
    elif content_type not in ("article", "chapter", "note", "video", "audio", "podcast", "music"):
        warnings.append(f"非常见 content_type: {content_type}")

    ctype = (data.get("content_type") or "article").strip().lower()
    if ctype == "video":
        if not data.get("video_path"):
            errors.append("content_type=video 时必须提供 video_path")
        if not data.get("cover_path") and not any(
            isinstance(m, dict) and m.get("role") == "cover" for m in (data.get("media_refs") or [])
        ):
            warnings.append("视频 manifest 建议提供 cover_path 或 media_refs.cover")
    elif ctype in ("audio", "podcast", "music"):
        if not data.get("audio_path") and not any(
            isinstance(m, dict) and m.get("role") == "audio" for m in (data.get("media_refs") or [])
        ):
            errors.append(f"content_type={ctype} 时必须提供 audio_path 或 media_refs.audio")
        if not data.get("copyright_notice"):
            warnings.append("音频/播客 manifest 建议提供 copyright_notice")
        if ctype == "podcast" and not data.get("show_notes_md"):
            warnings.append("podcast 建议提供 show_notes_md")
    elif not data.get("body_md") and not data.get("body_html"):
        errors.append("必须提供 body_md 或 body_html 之一")

    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("targets 必须为非空数组")
    else:
        for i, target in enumerate(targets):
            if not isinstance(target, dict):
                errors.append(f"targets[{i}] 必须是对象")
                continue
            for tkey in ("platform_account_id", "adapter_type"):
                if not target.get(tkey):
                    errors.append(f"targets[{i}] 缺少 {tkey}")
            if target.get("review_required") is True:
                warnings.append(f"targets[{i}] 需要人工审核 (review_required=true)")

    media_refs = data.get("media_refs")
    if media_refs is not None and not isinstance(media_refs, list):
        errors.append("media_refs 必须是数组")

    return ManifestValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_manifest_file(path: Path) -> tuple[dict[str, Any] | None, ManifestValidationResult]:
    try:
        data = load_manifest(path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, ManifestValidationResult(ok=False, errors=[str(exc)])
    return data, validate_manifest(data)
