"""封面设置与批量操作（cover_path + cover_config_json）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web.uploads import save_cover_file


def normalize_cover_config(raw: str | dict | None) -> str | None:
    """校验并返回可写入 cover_config_json 列的 JSON 字符串。"""
    if raw is None or raw == "":
        return None
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict):
        raise ValueError("cover_config 必须是 JSON 对象")
    crop = data.get("crop")
    if crop is not None:
        if not isinstance(crop, dict):
            raise ValueError("cover_config.crop 必须是对象")
        for key in ("x", "y", "width", "height"):
            if key in crop and not isinstance(crop[key], (int, float)):
                raise ValueError(f"cover_config.crop.{key} 必须是数字")
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def resolve_cover_config(
    conn: Any,
    *,
    explicit: str | None = None,
    reuse_from_article_id: int | None = None,
) -> str | None:
    """解析封面位置配置：显式 JSON 优先，否则从源作品复制。"""
    if explicit:
        return normalize_cover_config(explicit)
    if reuse_from_article_id is None:
        return None
    row = conn.execute(
        "SELECT cover_config_json FROM articles WHERE id = ?",
        (int(reuse_from_article_id),),
    ).fetchone()
    if row is None:
        raise ValueError("复用封面位置的源作品不存在")
    cfg = (row["cover_config_json"] or "").strip()
    return cfg or None


def _active_article_ids(conn: Any, article_ids: list[int]) -> list[int]:
    out: list[int] = []
    for aid in article_ids:
        row = conn.execute(
            """
            SELECT id FROM articles
            WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')
            """,
            (int(aid),),
        ).fetchone()
        if row:
            out.append(int(row["id"]))
    return out


def apply_cover_to_articles(
    conn: Any,
    article_ids: list[int],
    *,
    cover_path: str,
    cover_config_json: str | None = None,
) -> dict[str, int]:
    """为多篇作品写入相同封面路径与可选位置配置。"""
    path = Path(cover_path)
    if not cover_path or not path.is_file():
        raise FileNotFoundError("封面文件不存在")
    valid_ids = _active_article_ids(conn, article_ids)
    skipped = len(article_ids) - len(valid_ids)
    for aid in valid_ids:
        conn.execute(
            """
            UPDATE articles
            SET cover_path = ?, cover_config_json = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (str(path), cover_config_json, aid),
        )
    return {"updated": len(valid_ids), "skipped": skipped}


def batch_set_cover_from_bytes(
    config: AppConfig,
    conn: Any,
    article_ids: list[int],
    *,
    filename: str,
    data: bytes,
    cover_config_json: str | None = None,
) -> dict[str, int]:
    dest = save_cover_file(config, filename, data)
    return apply_cover_to_articles(
        conn,
        article_ids,
        cover_path=str(dest),
        cover_config_json=cover_config_json,
    )


def batch_set_cover_from_path(
    conn: Any,
    article_ids: list[int],
    *,
    cover_path: str,
    cover_config_json: str | None = None,
) -> dict[str, int]:
    return apply_cover_to_articles(
        conn,
        article_ids,
        cover_path=cover_path,
        cover_config_json=cover_config_json,
    )


def batch_set_cover_from_article(
    conn: Any,
    article_ids: list[int],
    *,
    source_article_id: int,
    cover_config_json: str | None = None,
) -> dict[str, int]:
    row = conn.execute(
        "SELECT cover_path FROM articles WHERE id = ?",
        (int(source_article_id),),
    ).fetchone()
    if row is None:
        raise ValueError("源作品不存在")
    cover_path = (row["cover_path"] or "").strip()
    if not cover_path:
        raise ValueError("源作品尚未设置封面")
    return apply_cover_to_articles(
        conn,
        article_ids,
        cover_path=cover_path,
        cover_config_json=cover_config_json,
    )
