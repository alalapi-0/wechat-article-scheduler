"""封面资产扫描、按 stem 绑定与孤儿清理。"""

from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import (
    InvalidCoverError,
    MAX_COVER_BYTES,
    SUPPORTED_COVER_EXTENSIONS,
    index_cover_directory,
    inspect_managed_cover,
    managed_cover_roots,
    secure_cover_snapshot,
)
from wechat_article_scheduler.filesystem_safety import (
    UnsafePathError,
    open_directory_handle,
    read_regular_file,
)

_ACTIVE_ARTICLE = "(deleted_at IS NULL OR deleted_at = '')"


def managed_cover_directories(config: AppConfig) -> list[Path]:
    """本地封面素材目录（上传目录优先）。"""
    roots = [
        config.covers_dir,
        config.root / "cover_assets",
        config.root / "assets" / "covers",
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = Path(os.path.abspath(root))
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            out.append(resolved)
    return out


def referenced_cover_paths(config: AppConfig, conn: sqlite3.Connection) -> set[Path]:
    refs: set[Path] = set()
    rows = conn.execute(
        "SELECT cover_path FROM articles WHERE cover_path IS NOT NULL AND cover_path != ''"
    ).fetchall()
    for row in rows:
        check = inspect_managed_cover(config, row["cover_path"] or "")
        if check["ok"]:
            refs.add(Path(str(check["resolved_path"])))
    try:
        from wechat_article_scheduler.content_library.collection_config import discover_collection_configs
        defaults = [item.default_cover for item in discover_collection_configs(config.root)]
    except (OSError, ValueError):
        defaults = []
    for raw in defaults:
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = config.root / candidate
        check = inspect_managed_cover(config, candidate)
        if check["ok"]:
            refs.add(Path(str(check["resolved_path"])))
    global_default = str(config.wechat_default_thumb_path or "").strip()
    if global_default:
        check = inspect_managed_cover(config, global_default)
        if check["ok"]:
            refs.add(Path(str(check["resolved_path"])))
    return refs


def _cover_identity(config: AppConfig, raw: str | Path) -> tuple[int, int] | None:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = config.root / candidate
    try:
        snapshot = read_regular_file(
            candidate,
            allowed_roots=managed_cover_roots(config),
            max_bytes=MAX_COVER_BYTES,
        )
    except UnsafePathError:
        return None
    return snapshot.device, snapshot.inode


def referenced_cover_identities(config: AppConfig, conn: sqlite3.Connection) -> set[tuple[int, int]]:
    return {
        identity
        for path in referenced_cover_paths(config, conn)
        if (identity := _cover_identity(config, path)) is not None
    }


def build_disk_stem_index(config: AppConfig) -> dict[str, str]:
    """磁盘封面按文件名 stem 索引（先出现的目录优先）。"""
    index: dict[str, str] = {}
    for root in managed_cover_directories(config):
        for asset in index_cover_directory(root):
            stem = Path(asset.name).stem
            index.setdefault(stem, asset.path)
    return index


def scan_cover_assets(config: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    """扫描素材库、绑定状态与孤儿封面。"""
    stem_index = build_disk_stem_index(config)
    assets: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for root in managed_cover_directories(config):
        for asset in index_cover_directory(root):
            if asset.path in seen_paths:
                continue
            seen_paths.add(asset.path)
            assets.append(
                {
                    "path": asset.path,
                    "name": asset.name,
                    "size_bytes": asset.size_bytes,
                    "source": str(root),
                }
            )

    rows = conn.execute(
        f"""
        SELECT id, title, source_path, cover_path
        FROM articles
        WHERE {_ACTIVE_ARTICLE}
        """
    ).fetchall()

    missing_cover: list[int] = []
    broken_bindings: list[dict[str, Any]] = []
    bindable: list[dict[str, Any]] = []

    for row in rows:
        aid = int(row["id"])
        cover_path = (row["cover_path"] or "").strip()
        stem = Path(row["source_path"] or "").stem
        if cover_path:
            if not inspect_managed_cover(config, cover_path)["ok"]:
                broken_bindings.append(
                    {
                        "article_id": aid,
                        "title": row["title"] or "",
                        "cover_path": cover_path,
                    }
                )
                suggested = stem_index.get(stem)
                if suggested:
                    bindable.append(
                        {
                            "article_id": aid,
                            "suggested_path": suggested,
                            "reason": "broken_binding",
                        }
                    )
        else:
            missing_cover.append(aid)
            suggested = stem_index.get(stem)
            if suggested:
                bindable.append(
                    {
                        "article_id": aid,
                        "suggested_path": suggested,
                        "reason": "missing_cover",
                    }
                )

    orphans = list_orphan_covers(config, conn)
    from wechat_article_scheduler.cover_assets.index import check_configured_cover
    default_check = check_configured_cover(config, None)

    human: list[str] = [
        f"素材库 {len(assets)} 张封面",
        f"{len(missing_cover)} 篇作品未设置封面",
    ]
    if broken_bindings:
        human.append(f"{len(broken_bindings)} 条封面路径无效")
    if bindable:
        human.append(f"{len(bindable)} 篇可按文件名自动绑定")
    if orphans:
        human.append(f"{len(orphans)} 个未引用封面文件可清理")
    if default_check.get("using_default"):
        human.append("未指定封面时将回退默认封面")

    return {
        "asset_count": len(assets),
        "assets": assets,
        "directories": [str(p) for p in managed_cover_directories(config)],
        "missing_cover_count": len(missing_cover),
        "missing_cover_ids": missing_cover[:50],
        "broken_binding_count": len(broken_bindings),
        "broken_bindings": broken_bindings[:50],
        "bindable_count": len(bindable),
        "bindable": bindable[:50],
        "orphan_count": len(orphans),
        "orphans": orphans[:50],
        "default_cover_check": default_check,
        "human": human,
    }


def bind_covers_by_stem(config: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    """为无封面或封面无效的作品，按 source_path stem 绑定磁盘封面。"""
    stem_index = build_disk_stem_index(config)
    if not stem_index:
        return {"bound": 0, "skipped": 0, "human": ["素材库中没有可绑定的封面文件"]}

    rows = conn.execute(
        f"""
        SELECT id, source_path, cover_path
        FROM articles
        WHERE {_ACTIVE_ARTICLE}
        """
    ).fetchall()
    bound = 0
    skipped = 0
    for row in rows:
        cover_path = (row["cover_path"] or "").strip()
        needs = not cover_path or not inspect_managed_cover(config, cover_path)["ok"]
        if not needs:
            skipped += 1
            continue
        stem = Path(row["source_path"] or "").stem
        suggested = stem_index.get(stem)
        if not suggested:
            skipped += 1
            continue
        conn.execute(
            """
            UPDATE articles
            SET cover_path = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (suggested, int(row["id"])),
        )
        bound += 1
    conn.commit()
    msg = f"已按文件名绑定 {bound} 篇作品封面"
    if skipped:
        msg += f"（跳过 {skipped} 篇）"
    return {"bound": bound, "skipped": skipped, "human": [msg]}


def repair_invalid_cover_paths(config: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    """清除数据库中指向不存在文件的 cover_path。"""
    rows = conn.execute(
        f"""
        SELECT id, cover_path FROM articles
        WHERE {_ACTIVE_ARTICLE}
          AND cover_path IS NOT NULL AND cover_path != ''
        """
    ).fetchall()
    cleared = 0
    for row in rows:
        path = (row["cover_path"] or "").strip()
        if path and inspect_managed_cover(config, path)["ok"]:
            continue
        conn.execute(
            """
            UPDATE articles
            SET cover_path = '', updated_at = datetime('now')
            WHERE id = ?
            """,
            (int(row["id"]),),
        )
        cleared += 1
    conn.commit()
    return {
        "cleared": cleared,
        "human": [
            f"已修复 {cleared} 条无效封面路径" if cleared else "没有需要修复的封面路径",
        ],
    }


def list_orphan_covers(config: AppConfig, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """列出各素材目录中未被任何作品引用的封面文件。"""
    refs = referenced_cover_identities(config, conn)
    root = config.root.resolve()
    orphans: list[dict[str, str]] = []
    seen: set[str] = set()
    for covers_dir in managed_cover_directories(config):
        try:
            directory = open_directory_handle(covers_dir, allowed_roots=(covers_dir,))
        except (OSError, UnsafePathError):
            continue
        try:
            with directory as handle:
                for name in handle.list_names():
                    path = covers_dir / name
                    if path.suffix.lower() not in SUPPORTED_COVER_EXTENSIONS:
                        continue
                    try:
                        snapshot = handle.read_regular_file(name, max_bytes=MAX_COVER_BYTES)
                        secure_cover_snapshot(snapshot, path.suffix)
                    except (UnsafePathError, InvalidCoverError):
                        continue
                    identity = (snapshot.device, snapshot.inode)
                    if identity in refs or str(path) in seen:
                        continue
                    seen.add(str(path))
                    try:
                        rel = str(path.relative_to(root))
                    except ValueError:
                        rel = str(path)
                    orphans.append({"path": rel, "name": name, "directory": str(covers_dir)})
        except (OSError, UnsafePathError):
            continue
    return orphans


def cleanup_orphan_covers(
    config: AppConfig,
    conn: sqlite3.Connection,
    *,
    unlink: Any,
) -> dict[str, Any]:
    """删除未引用封面；unlink 必须支持受控目录句柄和文件快照。"""
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    else:
        conn.execute("UPDATE articles SET updated_at = updated_at WHERE 0")
    items: list[dict[str, str]] = []
    removed = 0
    root = config.root.resolve()
    seen: set[str] = set()
    for covers_dir in managed_cover_directories(config):
        try:
            directory = open_directory_handle(covers_dir, allowed_roots=(covers_dir,))
        except (OSError, UnsafePathError):
            continue
        try:
            with directory as handle:
                for name in handle.list_names():
                    path = covers_dir / name
                    if path.suffix.lower() not in SUPPORTED_COVER_EXTENSIONS:
                        continue
                    try:
                        snapshot = handle.read_regular_file(name, max_bytes=MAX_COVER_BYTES)
                        secure_cover_snapshot(snapshot, path.suffix)
                    except (UnsafePathError, InvalidCoverError):
                        continue
                    identity = (snapshot.device, snapshot.inode)
                    if identity in referenced_cover_identities(config, conn) or str(path) in seen:
                        continue
                    seen.add(str(path))
                    try:
                        rel = str(path.relative_to(root))
                    except ValueError:
                        rel = str(path)
                    item = {"path": rel, "name": name, "directory": str(covers_dir)}
                    items.append(item)
                    if identity in referenced_cover_identities(config, conn):
                        continue
                    if unlink(
                        config,
                        item["path"],
                        directory_handle=handle,
                        snapshot=snapshot,
                    ):
                        removed += 1
        except (OSError, UnsafePathError):
            continue
    return {
        "scanned": len(items),
        "removed": removed,
        "orphans": items,
        "human": [
            f"已清理 {removed} 个未引用封面文件"
            if removed
            else "没有发现可安全删除的未引用封面",
        ],
    }
