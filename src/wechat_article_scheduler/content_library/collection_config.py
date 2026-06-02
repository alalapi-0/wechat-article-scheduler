"""多合集 collection.yaml 解析（Round 63 / 收敛 Phase 1 Round 8）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from wechat_article_scheduler.content_library.repository import slugify


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
    dirs: list[Path] = []
    custom = raw.get("inbox_dir")
    if custom:
        p = Path(str(custom))
        dirs.append(p if p.is_absolute() else root / p)
    default_coll = root / "content" / "collections" / slug / "inbox"
    if default_coll not in dirs:
        dirs.append(default_coll)
    legacy = raw.get("legacy_inbox_subdir") or slug
    legacy_path = root / "articles" / "inbox" / str(legacy)
    if legacy_path not in dirs:
        dirs.append(legacy_path)
    out: list[Path] = []
    seen: set[str] = set()
    for d in dirs:
        key = str(d.resolve()) if d.exists() or True else str(d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return tuple(out)


def load_collection_yaml(path: Path, *, root: Path) -> CollectionConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"collection.yaml 必须是对象: {path}")
    name = str(data.get("name") or path.parent.name).strip()
    slug = str(data.get("slug") or slugify(name)).strip()
    if not slug:
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
    if not base.is_dir():
        return []
    configs: list[CollectionConfig] = []
    for yaml_path in sorted(base.glob("*/collection.yaml")):
        try:
            configs.append(load_collection_yaml(yaml_path, root=root))
        except (OSError, ValueError, yaml.YAMLError):
            continue
    return configs
