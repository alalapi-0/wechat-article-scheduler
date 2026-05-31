"""网页批量上传：把用户上传的作品文件与封面图落地并入库（Round 44）。

设计：保持 FastAPI 细节在 app.py，本模块只处理 (filename, bytes) 元组，便于单测。
- 作品文件 → 写入收件箱（config.inbox_dir），随后复用 scan_inbox 解析入库。
- 封面图 → 写入 articles/covers/，按文件名（去扩展名）与作品自动配对，写入 articles.cover_path。
"""

from __future__ import annotations

import re
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scanner import scan_inbox

ARTICLE_EXTENSIONS = {".md", ".markdown", ".txt", ".html", ".htm"}
COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

_UNSAFE = re.compile(r"[^\w.\-\u4e00-\u9fff]+")


def safe_filename(name: str) -> str:
    """清洗上传文件名，移除路径分隔符与危险字符。"""
    base = Path(name or "").name.strip() or "unnamed"
    cleaned = _UNSAFE.sub("_", base).strip("._") or "unnamed"
    return cleaned


def _unique_path(path: Path) -> Path:
    """若目标已存在则追加序号，避免覆盖。"""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def save_cover_file(config: AppConfig, filename: str, data: bytes) -> Path:
    """保存单个封面文件，返回落地路径。"""
    target_dir = config.covers_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_path(target_dir / safe_filename(filename))
    dest.write_bytes(data)
    return dest


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
    inbox.mkdir(parents=True, exist_ok=True)

    saved_articles = 0
    skipped_articles: list[str] = []
    for name, data in articles:
        suffix = Path(name or "").suffix.lower()
        if suffix not in ARTICLE_EXTENSIONS:
            skipped_articles.append(safe_filename(name))
            continue
        dest = _unique_path(inbox / safe_filename(name))
        dest.write_bytes(data)
        saved_articles += 1

    cover_by_stem: dict[str, str] = {}
    skipped_covers: list[str] = []
    for name, data in covers:
        suffix = Path(name or "").suffix.lower()
        if suffix not in COVER_EXTENSIONS:
            skipped_covers.append(safe_filename(name))
            continue
        dest = save_cover_file(config, name, data)
        cover_by_stem[Path(safe_filename(name)).stem] = str(dest)

    scan_stats = scan_inbox(config) if saved_articles else {
        "scanned": 0,
        "imported": 0,
        "skipped_duplicate": 0,
        "errors": 0,
    }
    matched_covers = _match_covers(config, cover_by_stem)

    human: list[str] = []
    if saved_articles:
        human.append(f"已上传 {saved_articles} 个作品文件")
    if cover_by_stem:
        human.append(f"已上传 {len(cover_by_stem)} 张封面")
    if scan_stats.get("imported"):
        human.append(f"新收录 {scan_stats['imported']} 篇作品")
    if matched_covers:
        human.append(f"已为 {matched_covers} 篇作品自动绑定封面")
    if scan_stats.get("skipped_duplicate"):
        human.append(f"有 {scan_stats['skipped_duplicate']} 篇是重复内容，已跳过")
    if skipped_articles:
        human.append(f"有 {len(skipped_articles)} 个文件格式不支持，未处理（支持 md/txt/html）")
    if skipped_covers:
        human.append(f"有 {len(skipped_covers)} 张图片格式不支持，未处理（支持 jpg/png/gif/webp）")
    if not human:
        human.append("没有可处理的文件，请选择 md/txt/html 作品或 jpg/png 封面")

    return {
        "saved_articles": saved_articles,
        "saved_covers": len(cover_by_stem),
        "matched_covers": matched_covers,
        "skipped_articles": skipped_articles,
        "skipped_covers": skipped_covers,
        "scan": scan_stats,
        "human": human,
    }
