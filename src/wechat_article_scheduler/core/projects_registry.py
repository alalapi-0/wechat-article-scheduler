"""多项目 projects.yaml 加载与校验（不写库，不替代 scan/plan）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProjectEntry:
    project_id: str
    display_name: str
    enabled: bool
    manifest_paths: list[Path]


@dataclass
class ProjectsRegistryValidation:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def default_projects_path(root: Path) -> Path:
    custom = root / "config" / "projects.yaml"
    if custom.exists():
        return custom
    return root / "config" / "projects.example.yaml"


def load_projects_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("projects.yaml 必须是 YAML 对象")
    return data


def validate_projects_registry(data: dict[str, Any]) -> ProjectsRegistryValidation:
    errors: list[str] = []
    warnings: list[str] = []
    version = data.get("schema_version")
    if version is None:
        errors.append("缺少 schema_version")
    elif version != 1:
        errors.append(f"不支持的 schema_version: {version!r}")

    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("projects 必须为非空数组")
        return ProjectsRegistryValidation(ok=False, errors=errors, warnings=warnings)

    seen_ids: set[str] = set()
    for i, item in enumerate(projects):
        if not isinstance(item, dict):
            errors.append(f"projects[{i}] 必须是对象")
            continue
        pid = str(item.get("project_id") or "").strip()
        if not pid:
            errors.append(f"projects[{i}] 缺少 project_id")
        elif pid in seen_ids:
            errors.append(f"重复的 project_id: {pid}")
        else:
            seen_ids.add(pid)
        manifests = item.get("manifests")
        if not isinstance(manifests, list) or not manifests:
            errors.append(f"projects[{i}] manifests 必须为非空数组")
        for j, mpath in enumerate(manifests or []):
            if not str(mpath).strip():
                errors.append(f"projects[{i}].manifests[{j}] 为空")

    if not any(isinstance(p, dict) and p.get("enabled", True) for p in projects):
        warnings.append("没有 enabled=true 的项目")

    return ProjectsRegistryValidation(ok=not errors, errors=errors, warnings=warnings)


def parse_projects_registry(
    data: dict[str, Any],
    *,
    root: Path,
) -> tuple[list[ProjectEntry], ProjectsRegistryValidation]:
    validation = validate_projects_registry(data)
    if not validation.ok:
        return [], validation

    entries: list[ProjectEntry] = []
    for item in data.get("projects") or []:
        if not isinstance(item, dict):
            continue
        enabled = bool(item.get("enabled", True))
        manifest_paths: list[Path] = []
        for rel in item.get("manifests") or []:
            manifest_paths.append((root / str(rel)).resolve())
        entries.append(
            ProjectEntry(
                project_id=str(item["project_id"]),
                display_name=str(item.get("display_name") or item["project_id"]),
                enabled=enabled,
                manifest_paths=manifest_paths,
            )
        )
    return entries, validation


def load_projects_registry(
    root: Path,
    projects_path: Path | None = None,
) -> tuple[list[ProjectEntry], dict[str, Any], ProjectsRegistryValidation]:
    path = projects_path or default_projects_path(root)
    if not path.exists():
        return (
            [],
            {},
            ProjectsRegistryValidation(
                ok=False,
                errors=[f"projects 文件不存在: {path}"],
            ),
        )
    try:
        data = load_projects_yaml(path)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return (
            [],
            {},
            ProjectsRegistryValidation(ok=False, errors=[str(exc)]),
        )
    entries, validation = parse_projects_registry(data, root=root)
    return entries, {"schema_version": data.get("schema_version"), "path": str(path.resolve())}, validation
