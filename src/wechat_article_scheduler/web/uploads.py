"""网页批量上传：把用户上传的作品文件与封面图落地并入库。

设计：保持 FastAPI 细节在 app.py，本模块只处理 (filename, bytes) 元组，便于单测。
- 作品文件 → 写入收件箱（config.inbox_dir），随后复用 scan_inbox 解析入库。
- 封面图 → 写入 articles/covers/，按文件名（去扩展名）与作品自动配对，写入 articles.cover_path。
"""

from __future__ import annotations

import re
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import (
    InvalidCoverError,
    SUPPORTED_COVER_EXTENSIONS,
    managed_cover_bytes,
    validate_image_bytes,
)
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.filesystem_safety import UnsafePathError, write_unique_file

ARTICLE_EXTENSIONS = {".md", ".markdown", ".txt", ".html", ".htm"}
COVER_EXTENSIONS = SUPPORTED_COVER_EXTENSIONS

_UNSAFE = re.compile(r"[^\w.\-\u4e00-\u9fff]+")


def _humanize_reconciled(reconciled: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for item in reconciled:
        title = str(item.get("title") or "该作品")
        if item.get("status_reset"):
            lines.append(f"《{title}》已在作品库中，已识别为重新上传并重置为待创建草稿")
        else:
            lines.append(f"《{title}》已在作品库中，可继续安排草稿创建")
    return lines


def safe_filename(name: str) -> str:
    """清洗上传文件名，移除路径分隔符与危险字符。"""
    base = Path(name or "").name.strip() or "unnamed"
    cleaned = _UNSAFE.sub("_", base).strip("._") or "unnamed"
    return cleaned


def save_cover_file(config: AppConfig, filename: str, data: bytes) -> Path:
    """保存单个封面文件，返回落地路径。"""
    safe_name = safe_filename(filename)
    validate_image_bytes(data, Path(safe_name).suffix)
    target_dir = config.covers_dir
    try:
        dest = write_unique_file(target_dir, safe_name, data, allowed_roots=(config.root,))
        managed_cover_bytes(config, dest)
        return dest
    except (OSError, UnsafePathError) as exc:
        raise InvalidCoverError("封面上传目录无效") from exc


def _match_covers(config: AppConfig, cover_by_stem: dict[str, str]) -> int:
    """为尚无封面的已收录作品，按文件名 stem 绑定封面。"""
    if not cover_by_stem:
        return 0
    matched = 0
    with db.connect(config.database_path) as conn:
        rows = conn.execute(
            "SELECT id, source_path FROM articles "
            "WHERE cover_path IS NULL OR cover_path = ''"
        ).fetchall()
        for row in rows:
            stem = Path(row["source_path"]).stem
            cover = cover_by_stem.get(stem)
            if cover:
                conn.execute(
                    "UPDATE articles SET cover_path = ?, updated_at = datetime('now') WHERE id = ?",
                    (cover, int(row["id"])),
                )
                matched += 1
        conn.commit()
    return matched


def handle_upload(
    config: AppConfig,
    *,
    articles: list[tuple[str, bytes]],
    covers: list[tuple[str, bytes]],
) -> dict:
    """落地上传文件、扫描入库并配对封面，返回人话摘要。"""
    inbox = config.inbox_dir
    saved_articles = 0
    skipped_articles: list[str] = []
    for name, data in articles:
        suffix = Path(name or "").suffix.lower()
        if suffix not in ARTICLE_EXTENSIONS:
            skipped_articles.append(safe_filename(name))
            continue
        try:
            write_unique_file(inbox, safe_filename(name), data, allowed_roots=(config.root,))
        except (OSError, UnsafePathError):
            skipped_articles.append(safe_filename(name))
            continue
        saved_articles += 1

    cover_by_stem: dict[str, str] = {}
    skipped_covers: list[str] = []
    for name, data in covers:
        suffix = Path(name or "").suffix.lower()
        if suffix not in COVER_EXTENSIONS:
            skipped_covers.append(safe_filename(name))
            continue
        try:
            dest = save_cover_file(config, name, data)
        except InvalidCoverError:
            skipped_covers.append(safe_filename(name))
            continue
        cover_by_stem[Path(safe_filename(name)).stem] = str(dest)

    scan_stats = scan_inbox(config) if saved_articles else {
        "scanned": 0,
        "imported": 0,
        "reconciled_reupload": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "reconciled_articles": [],
    }
    matched_covers = _match_covers(config, cover_by_stem)
    reconciled = scan_stats.get("reconciled_articles") or []

    human: list[str] = []
    if saved_articles:
        human.append(f"已上传 {saved_articles} 个作品文件")
    if cover_by_stem:
        human.append(f"已上传 {len(cover_by_stem)} 张封面")
    if scan_stats.get("imported"):
        human.append(f"新收录 {scan_stats['imported']} 篇作品")
    if reconciled:
        human.extend(_humanize_reconciled(reconciled))
    if matched_covers:
        human.append(f"已为 {matched_covers} 篇作品自动绑定封面")
    if scan_stats.get("skipped_duplicate"):
        human.append(f"有 {scan_stats['skipped_duplicate']} 篇是重复内容，已跳过")
    if scan_stats.get("skipped_empty"):
        human.append(f"有 {scan_stats['skipped_empty']} 个空文件已跳过，未入库")
    if skipped_articles:
        human.append(f"有 {len(skipped_articles)} 个文件格式不支持，未处理（支持 md/txt/html）")
    if skipped_covers:
        human.append(f"有 {len(skipped_covers)} 张图片格式不支持，未处理（仅支持 jpg/jpeg/png）")
    if not human:
        human.append("没有可处理的文件，请选择 md/txt/html 作品或 jpg/png 封面")

    return {
        "saved_articles": saved_articles,
        "saved_covers": len(cover_by_stem),
        "matched_covers": matched_covers,
        "skipped_articles": skipped_articles,
        "skipped_covers": skipped_covers,
        "scan": scan_stats,
        "reconciled_articles": reconciled,
        "human": human,
    }
