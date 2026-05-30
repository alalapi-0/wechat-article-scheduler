"""封面素材索引与发布前检查（Round 14）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverAsset:
    path: str
    name: str
    exists: bool
    size_bytes: int | None


def index_cover_directory(root: Path) -> list[CoverAsset]:
    """索引 cover_assets 目录下的图片文件。"""
    if not root.is_dir():
        return []
    exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    assets: list[CoverAsset] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        assets.append(
            CoverAsset(
                path=str(path),
                name=path.name,
                exists=True,
                size_bytes=path.stat().st_size,
            )
        )
    return assets


def check_cover_path(path: Path | None, *, default_thumb: Path | None = None) -> dict[str, object]:
    """检查封面路径是否可用于发布。"""
    if path is None or not str(path).strip():
        if default_thumb and default_thumb.is_file():
            return {
                "ok": True,
                "using_default": True,
                "resolved_path": str(default_thumb),
                "message": "未指定封面，将使用默认封面",
            }
        return {
            "ok": False,
            "using_default": False,
            "message": "缺少封面且未配置默认封面",
        }
    if not path.is_file():
        return {"ok": False, "message": f"封面路径无效: {path}"}
    if path.stat().st_size <= 0:
        return {"ok": False, "message": f"封面文件为空: {path}"}
    return {"ok": True, "resolved_path": str(path), "message": "封面可用"}
