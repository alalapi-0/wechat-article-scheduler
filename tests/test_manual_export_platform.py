"""Round 78：manual_export 平台提示包。"""

from __future__ import annotations

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


def _seed(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(tmp_path, tmp_path / "z.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/a.md', 'T', 'S', 'body', 'h', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return cfg, int(aid)


def test_zhihu_platform_pack(tmp_path: Path) -> None:
    cfg, aid = _seed(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_article_to_outbox(cfg, conn, aid, platform="zhihu")
    assert result["ok"]
    assert (Path(result["outbox_path"]) / "zhihu_copy.md").is_file()


def test_phase2_doc_exists() -> None:
    text = (Path(__file__).resolve().parents[1] / "docs" / "phase2_text_platforms.md").read_text(
        encoding="utf-8"
    )
    assert "manual_export" in text
    assert "Phase 1" in text
