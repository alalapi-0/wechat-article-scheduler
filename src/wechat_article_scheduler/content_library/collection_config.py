"""多合集 collection.yaml 解析。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

import yaml

from wechat_article_scheduler.content_library.repository import slugify
from wechat_article_scheduler.filesystem_safety import (
    FileSnapshot,
    UnsafePathError,
    is_under,
    open_directory_handle,
    read_regular_file,
)

_SAFE_SLUG = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class CollectionConfig:
    slug: str
    name: str
    description: str
    volume_label: str | None
    title_template: str | None
    default_cover: str | None
    sort_rule: str
    inbox_dirs: tuple[Path, ...]
    yaml_path: Path
    schedule_raw: dict[str, Any] | None = None

    def to_config_json(self) -> str:
        import json

        payload = {
            "volume_label": self.volume_label,
            "title_template": self.title_template,
            "default_cover": self.default_cover,
            "sort_rule": self.sort_rule,
            "inbox_dirs": [str(p) for p in self.inbox_dirs],
            "yaml_path": str(self.yaml_path),
            "schedule": self.schedule_raw,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def apply_title_template(template: str | None, title: str) -> str:
    if not template or "{title}" not in template:
        return title
    return template.replace("{title}", title).strip()


def _resolve_inbox_dirs(root: Path, slug: str, raw: dict[str, Any]) -> tuple[Path, ...]:
    if not _SAFE_SLUG.fullmatch(slug) or slug in {".", ".."}:
        raise ValueError("合集 slug 只能包含字母、数字、下划线和连字符")
    approved = (root / "content" / "collections", root / "articles" / "inbox")
    dirs: list[Path] = []
    custom = raw.get("inbox_dir")
    if custom:
        p = Path(str(custom))
        candidate = p if p.is_absolute() else root / p
        if not is_under(candidate, approved):
            raise ValueError("合集 inbox_dir 超出允许目录")
        dirs.append(candidate)
    default_coll = root / "content" / "collections" / slug / "inbox"
    if default_coll not in dirs:
        dirs.append(default_coll)
    legacy = raw.get("legacy_inbox_subdir") or slug
    if not _SAFE_SLUG.fullmatch(str(legacy)) or str(legacy) in {".", ".."}:
        raise ValueError("legacy_inbox_subdir 无效")
    legacy_path = root / "articles" / "inbox" / str(legacy)
    if legacy_path not in dirs:
        dirs.append(legacy_path)
    out: list[Path] = []
    seen: set[str] = set()
    for d in dirs:
        key = str(d.absolute())
        if key not in seen:
            seen.add(key)
            out.append(d)
    return tuple(out)


def load_collection_yaml(path: Path, *, root: Path) -> CollectionConfig:
    snapshot = read_regular_file(path, allowed_roots=(root / "content" / "collections",))
    return _load_collection_snapshot(path, snapshot, root=root)


def _load_collection_snapshot(
    path: Path, snapshot: FileSnapshot, *, root: Path
) -> CollectionConfig:
    data = yaml.safe_load(snapshot.data.decode("utf-8", errors="strict")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"collection.yaml 必须是对象: {path}")
    name = str(data.get("name") or path.parent.name).strip()
    slug = str(data.get("slug") or slugify(name)).strip()
    if not slug or not _SAFE_SLUG.fullmatch(slug) or slug in {".", ".."}:
        raise ValueError(f"合集 slug 无效: {path}")
    sched = data.get("schedule")
    schedule_raw = sched if isinstance(sched, dict) else None
    return CollectionConfig(
        slug=slug,
        name=name,
        description=str(data.get("description") or "").strip(),
        volume_label=(str(data["volume_label"]).strip() if data.get("volume_label") else None),
        title_template=(str(data["title_template"]).strip() if data.get("title_template") else None),
        default_cover=(str(data["default_cover"]).strip() if data.get("default_cover") else None),
        sort_rule=str(data.get("sort_rule") or "source_name").strip(),
        inbox_dirs=_resolve_inbox_dirs(root, slug, data),
        yaml_path=path,
        schedule_raw=schedule_raw,
    )


def discover_collection_configs(root: Path) -> list[CollectionConfig]:
    """扫描 content/collections/*/collection.yaml。"""
    base = root / "content" / "collections"
    try:
        directory = open_directory_handle(base, allowed_roots=(base,))
    except (OSError, UnsafePathError):
        return []
    configs: list[CollectionConfig] = []
    try:
        with directory as base_handle:
            for name in base_handle.list_names():
                if not _SAFE_SLUG.fullmatch(name) or name in {".", ".."}:
                    continue
                yaml_path = base / name / "collection.yaml"
                try:
                    with base_handle.open_child_directory(name) as collection_handle:
                        snapshot = collection_handle.read_regular_file("collection.yaml")
                        configs.append(_load_collection_snapshot(yaml_path, snapshot, root=root))
                except (OSError, UnsafePathError, ValueError, yaml.YAMLError, UnicodeDecodeError):
                    continue
    except (OSError, UnsafePathError):
        return configs
    return configs
