"""Phase5 统一 outbox 预研：只读聚合导出目录与 publish_manifest 汇总（不移动文件）。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from wechat_article_scheduler.adapters.manual_export.platforms import SUPPORTED_PLATFORMS
from wechat_article_scheduler.core.manifest_loader import validate_manifest_file
from wechat_article_scheduler.core.projects_registry import default_projects_path, load_projects_registry

DEFAULT_SCAN_ROOTS = ("outbox",)


def default_unified_outbox_config_path(root: Path) -> Path:
    custom = root / "config" / "unified_outbox.yaml"
    if custom.exists():
        return custom
    return root / "config" / "unified_outbox.example.yaml"


def load_unified_outbox_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": 1,
            "scan_roots": list(DEFAULT_SCAN_ROOTS),
            "include_publish_manifests_from_projects": True,
        }
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _inventory_package_dir(package_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for child in sorted(package_dir.iterdir()):
        if child.is_file():
            files.append(
                {
                    "name": child.name,
                    "size_bytes": child.stat().st_size,
                    "role": _guess_file_role(child.name),
                }
            )
    manifest_path = package_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {"_parse_error": True}
    return {
        "name": package_dir.name,
        "path": str(package_dir.resolve()),
        "relative_path": package_dir.name,
        "modified_at": package_dir.stat().st_mtime,
        "file_count": len(files),
        "files": files,
        "export_manifest": manifest,
        "platform": str(manifest.get("platform") or "generic"),
        "article_id": manifest.get("article_id"),
        "title": manifest.get("title"),
        "exported_at": manifest.get("exported_at"),
    }


def _guess_file_role(filename: str) -> str:
    lower = filename.lower()
    if lower == "manifest.json":
        return "manifest"
    if lower in ("readme.txt", "instructions.txt", "说明.txt"):
        return "instructions"
    if "cover" in lower:
        return "cover"
    if lower.endswith((".md", ".html")):
        return "content"
    return "asset"


def index_outbox_directories(
    root: Path,
    *,
    scan_roots: list[str] | None = None,
    limit_per_root: int = 50,
) -> dict[str, Any]:
    """只读扫描导出目录，按平台聚合索引。"""
    roots = scan_roots or list(DEFAULT_SCAN_ROOTS)
    packages: list[dict[str, Any]] = []
    errors: list[str] = []

    for rel in roots:
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        dirs = [p for p in base.iterdir() if p.is_dir()]
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for package_dir in dirs[:limit_per_root]:
            try:
                entry = _inventory_package_dir(package_dir)
                entry["scan_root"] = rel
                packages.append(entry)
            except OSError as exc:
                errors.append(f"{package_dir}: {exc}")

    by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pkg in packages:
        by_platform[pkg["platform"]].append(
            {
                "name": pkg["name"],
                "relative_path": f"{pkg['scan_root']}/{pkg['name']}",
                "title": pkg.get("title"),
                "article_id": pkg.get("article_id"),
                "exported_at": pkg.get("exported_at"),
                "file_count": pkg["file_count"],
            }
        )

    known_platforms = sorted(SUPPORTED_PLATFORMS.keys())
    platform_index = [
        {
            "platform": key,
            "package_count": len(by_platform.get(key, [])),
            "packages": by_platform.get(key, []),
            "registered": key in SUPPORTED_PLATFORMS,
        }
        for key in sorted(set(list(by_platform.keys()) + known_platforms))
        if by_platform.get(key) or key in known_platforms
    ]

    return {
        "scan_roots": roots,
        "package_count": len(packages),
        "platform_count": len([p for p in platform_index if p["package_count"] > 0]),
        "packages": packages,
        "by_platform": dict(by_platform),
        "platform_index": platform_index,
        "errors": errors,
    }


def summarize_publish_manifests(
    root: Path,
    *,
    projects_path: Path | None = None,
) -> dict[str, Any]:
    """汇总 projects.yaml 中的 publish_manifest 路径（校验 + 干跑元数据，不写库）。"""
    path = projects_path or default_projects_path(root)
    entries, meta, validation = load_projects_registry(root, projects_path)
    manifests: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.enabled:
            continue
        for mpath in entry.manifest_paths:
            _data, mval = validate_manifest_file(mpath)
            targets = len((_data or {}).get("targets") or [])
            manifests.append(
                {
                    "project_id": entry.project_id,
                    "manifest_path": str(mpath.resolve()),
                    "validation_ok": mval.ok,
                    "target_count": targets,
                    "errors": mval.errors,
                    "warnings": mval.warnings,
                }
            )
    return {
        "projects_path": str(path.resolve()),
        "registry_ok": validation.ok,
        "manifest_count": len(manifests),
        "manifests": manifests,
    }


def build_unified_outbox_dry_run(
    root: Path,
    *,
    config_path: Path | None = None,
    projects_path: Path | None = None,
) -> dict[str, Any]:
    cfg_path = config_path or default_unified_outbox_config_path(root)
    cfg = load_unified_outbox_config(cfg_path)
    scan_roots = [str(r) for r in (cfg.get("scan_roots") or DEFAULT_SCAN_ROOTS)]
    outbox_index = index_outbox_directories(root, scan_roots=scan_roots)

    manifest_summary: dict[str, Any] | None = None
    if cfg.get("include_publish_manifests_from_projects", True):
        manifest_summary = summarize_publish_manifests(root, projects_path=projects_path)

    registry_ok = True
    if manifest_summary is not None:
        registry_ok = manifest_summary.get("registry_ok", True)

    return {
        "ok": registry_ok and not outbox_index.get("errors"),
        "phase": "phase5_unified_outbox",
        "mode": "dry_run",
        "config_path": str(cfg_path.resolve()),
        "guardrails": cfg.get("guardrails")
        or [
            "导出包不等于已发布",
            "不移动 outbox 或 articles 文件",
            "proof 须人工确认",
        ],
        "outbox_index": outbox_index,
        "publish_manifest_summary": manifest_summary,
        "supported_export_platforms": list(SUPPORTED_PLATFORMS.keys()),
        "wechat_mainline": "articles/ 与 scan/plan 独立；outbox 仅人工导出索引",
        "note": "统一 outbox 预研；只读目录清单，不执行移动/删除/标记发布。",
    }
