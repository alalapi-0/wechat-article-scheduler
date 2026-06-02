"""将作品导出为 outbox 目录（Phase 2 Round 23 / manual_export）。"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_preview import render_for_publish

OUTBOX_VERSION = 1

_PLATFORM_PACKS: dict[str, str] = {
    "zhihu": "zhihu_copy.md",
    "douban": "douban_copy.md",
}


def _write_platform_pack(
    dest: Path, *, platform: str, title: str, digest: str
) -> str | None:
    key = (platform or "generic").strip().lower()
    if key == "generic" or key not in _PLATFORM_PACKS:
        return None
    fname = _PLATFORM_PACKS[key]
    hints = {
        "zhihu": [
            "# 知乎发布提示",
            "",
            f"建议标题：{title}",
            f"建议摘要/导语：{digest}",
            "",
            "- 从 `article.md` 或 `article.html` 复制正文",
            "- 封面使用 `cover.*`（若有）",
            "- 发布后在作品详情提交 proof，勿在本地标为已发布",
        ],
        "douban": [
            "# 豆瓣发布提示",
            "",
            f"标题：{title}",
            "",
            "- 从 `article.md` 复制正文",
            "- 标签与频道需在豆瓣后台手动选择",
            "- 发布后在作品详情提交 proof",
        ],
    }
    dest.joinpath(fname).write_text("\n".join(hints[key]) + "\n", encoding="utf-8")
    return fname


def outbox_root(config: AppConfig) -> Path:
    root = config.root / "outbox"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_slug(title: str, article_id: int) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", (title or "untitled").strip())[:40].strip("-")
    return base or f"article-{article_id}"


def _article_row(conn: Any, article_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, title, summary, body, status, source_path, cover_path, updated_at
        FROM articles
        WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')
        """,
        (article_id,),
    ).fetchone()
    return dict(row) if row else None


def export_article_to_outbox(
    config: AppConfig,
    conn: Any,
    article_id: int,
    *,
    platform: str = "generic",
) -> dict[str, Any]:
    """导出 Markdown/HTML/封面与说明；不修改发布状态、不联网。"""
    row = _article_row(conn, article_id)
    if not row:
        return {"ok": False, "error": "作品不存在"}

    title = row["title"] or ""
    summary = row["summary"] or ""
    body = row["body"] or ""
    digest = clamp_summary((summary or "").strip() or title, 120)
    slug = _safe_slug(title, article_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = outbox_root(config) / f"{slug}_{article_id}_{stamp}"
    if dest.exists():
        return {"ok": False, "error": "outbox 目录已存在，请稍后重试"}
    dest.mkdir(parents=True)

    md_path = dest / "article.md"
    md_path.write_text(
        f"# {title}\n\n> 摘要：{digest}\n\n{body}\n",
        encoding="utf-8",
    )
    html_path = dest / "article.html"
    html_path.write_text(
        f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>"
        f"<title>{title}</title></head><body>{render_for_publish(title, body)}</body></html>",
        encoding="utf-8",
    )

    files_written = ["article.md", "article.html"]
    cover_dest: str | None = None
    cover_src = (row.get("cover_path") or "").strip()
    if cover_src and Path(cover_src).is_file():
        ext = Path(cover_src).suffix or ".png"
        cover_dest = str(dest / f"cover{ext}")
        shutil.copy2(cover_src, cover_dest)
        files_written.append(Path(cover_dest).name)

    instructions = dest / "INSTRUCTIONS.md"
    instructions.write_text(
        "\n".join(
            [
                "# 手动发布说明",
                "",
                "本目录由 **manual_export** 生成，仅便于复制到其他平台。",
                "",
                "- 不会自动登录任何平台",
                "- 不会将作品标记为「已发布」",
                "- 复制上传后请在作品详情提交 **发布证明（proof）**",
                "",
                "## 文件",
                "",
                "- `article.md` — Markdown 正文",
                "- `article.html` — 公众号风格 HTML 预览稿",
                "- `cover.*` — 封面图（若有）",
                "- `manifest.json` — 元数据",
                "",
            ]
        ),
        encoding="utf-8",
    )
    files_written.append("INSTRUCTIONS.md")

    manifest = {
        "outbox_version": OUTBOX_VERSION,
        "platform": platform,
        "article_id": article_id,
        "title": title,
        "digest_preview": digest,
        "exported_at": stamp,
        "source_path": row.get("source_path"),
        "status_at_export": row.get("status"),
        "files": files_written,
        "proof_required": True,
        "note": "导出成功不等于发布成功",
    }
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    files_written.append("manifest.json")

    platform_file = _write_platform_pack(dest, platform=platform, title=title, digest=digest)
    if platform_file:
        files_written.append(platform_file)

    db.log_event(
        conn,
        entity_type="article",
        entity_id=article_id,
        event_type="outbox_exported",
        payload=json.dumps(
            {"outbox_path": str(dest), "platform": platform, "files": files_written},
            ensure_ascii=False,
        ),
    )
    conn.commit()

    return {
        "ok": True,
        "article_id": article_id,
        "outbox_path": str(dest),
        "relative_path": str(dest.relative_to(config.root)),
        "files": files_written,
        "manifest": manifest,
        "human": [
            f"已导出 outbox 包：{dest.name}",
            "请手动复制到目标平台后，在作品详情回填发布证明",
        ],
    }


def list_outbox_packages(config: AppConfig, *, limit: int = 30) -> list[dict[str, Any]]:
    """列出最近 outbox 目录（按修改时间倒序）。"""
    root = outbox_root(config)
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in dirs[:limit]:
        manifest_path = path / "manifest.json"
        meta: dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                meta = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        out.append(
            {
                "name": path.name,
                "path": str(path),
                "relative_path": str(path.relative_to(config.root)),
                "article_id": meta.get("article_id"),
                "title": meta.get("title"),
                "exported_at": meta.get("exported_at"),
                "platform": meta.get("platform", "generic"),
            }
        )
    return out
