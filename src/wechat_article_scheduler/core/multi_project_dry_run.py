"""多项目 manifest 批量干跑（基于 round_086/087 manifest 能力，不写库）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wechat_article_scheduler.content_packages.from_manifest import manifest_dry_run_summary
from wechat_article_scheduler.core.manifest_loader import (
    load_manifest,
    validate_manifest_file,
)
from wechat_article_scheduler.core.projects_registry import (
    ProjectEntry,
    load_projects_registry,
)


def _dry_run_one_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {
            "manifest_path": str(manifest_path),
            "ok": False,
            "error": "manifest 文件不存在",
        }
    _data, validation = validate_manifest_file(manifest_path)
    if not validation.ok:
        return {
            "manifest_path": str(manifest_path.resolve()),
            "ok": False,
            "validation": validation.to_dict(),
        }
    try:
        summary = manifest_dry_run_summary(load_manifest(manifest_path))
    except ValueError as exc:
        return {
            "manifest_path": str(manifest_path.resolve()),
            "ok": False,
            "error": str(exc),
        }
    manifest_project = summary.get("content_package", {}).get("project_id")
    return {
        "manifest_path": str(manifest_path.resolve()),
        "ok": True,
        "validation": summary.get("validation"),
        "dry_run": summary,
        "manifest_project_id": manifest_project,
    }


def dry_run_project(entry: ProjectEntry) -> dict[str, Any]:
    results = [_dry_run_one_manifest(path) for path in entry.manifest_paths]
    manifest_ids = [
        r.get("manifest_project_id") or r.get("dry_run", {})
        .get("content_package", {})
        .get("project_id")
        for r in results
        if r.get("ok")
    ]
    id_mismatch = any(mid and mid != entry.project_id for mid in manifest_ids)
    return {
        "project_id": entry.project_id,
        "display_name": entry.display_name,
        "enabled": entry.enabled,
        "manifest_count": len(results),
        "ok": all(r.get("ok") for r in results) and not id_mismatch,
        "project_id_mismatch": id_mismatch,
        "manifests": results,
    }


def build_multi_project_dry_run(
    root: Path,
    *,
    projects_path: Path | None = None,
) -> dict[str, Any]:
    entries, meta, registry_validation = load_projects_registry(root, projects_path)
    if not registry_validation.ok:
        return {
            "ok": False,
            "phase": "phase5_multi_project",
            "mode": "dry_run",
            "registry": registry_validation.to_dict(),
            "projects_path": meta.get("path"),
            "wechat_mainline": "scan/plan/run-once 未调用",
            "note": "多项目干跑失败：projects 注册表无效",
        }

    active = [e for e in entries if e.enabled]
    project_results = [dry_run_project(e) for e in active]
    all_ok = all(p["ok"] for p in project_results)

    return {
        "ok": all_ok,
        "phase": "phase5_multi_project",
        "mode": "dry_run",
        "projects_path": meta.get("path"),
        "schema_version": meta.get("schema_version"),
        "registry": registry_validation.to_dict(),
        "project_count": len(active),
        "manifest_count": sum(p["manifest_count"] for p in project_results),
        "projects": project_results,
        "wechat_mainline": "scan/plan/run-once 未调用",
        "note": "多项目 manifest 干跑；未写入数据库，不替代微信收件箱 scan/plan。",
    }


def projects_registry_summary(
    root: Path,
    *,
    projects_path: Path | None = None,
) -> dict[str, Any]:
    entries, meta, validation = load_projects_registry(root, projects_path)
    return {
        "ok": validation.ok,
        "projects_path": meta.get("path"),
        "schema_version": meta.get("schema_version"),
        "validation": validation.to_dict(),
        "projects": [
            {
                "project_id": e.project_id,
                "display_name": e.display_name,
                "enabled": e.enabled,
                "manifest_paths": [str(p) for p in e.manifest_paths],
            }
            for e in entries
        ],
        "wechat_mainline": "articles/inbox + scan/plan 仍为 P0",
    }
