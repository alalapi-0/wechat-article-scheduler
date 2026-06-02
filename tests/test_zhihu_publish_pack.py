"""Round 79：知乎发布包模板增强。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "zhihu_publish_pack.md"

ZHIHU_FILES = (
    "zhihu_title.txt",
    "zhihu_excerpt.txt",
    "zhihu_body.md",
    "zhihu_cover_notes.txt",
    "zhihu_publish_checklist.md",
    "zhihu_publish.md",
)


def _seed(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(tmp_path, tmp_path / "z.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/z.md', '知乎测试标题', '这是导语', '正文段落', 'hz', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return cfg, int(aid)


def test_zhihu_pack_includes_all_fields(tmp_path: Path) -> None:
    cfg, aid = _seed(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_article_to_outbox(cfg, conn, aid, platform="zhihu")
    assert result["ok"]
    out = Path(result["outbox_path"])
    for name in ZHIHU_FILES:
        assert (out / name).is_file(), name
    assert "知乎测试标题" in (out / "zhihu_title.txt").read_text(encoding="utf-8")
    assert result["manifest"]["platform"] == "zhihu"


def test_api_platforms_list(tmp_path: Path) -> None:
    cfg, aid = _seed(tmp_path)
    client = TestClient(create_app(cfg))
    plats = client.get("/api/manual-export/platforms").json()
    ids = {p["id"] for p in plats["platforms"]}
    assert "zhihu" in ids
    r = client.post(f"/api/articles/{aid}/export-outbox?platform=zhihu")
    assert r.json()["ok"]


def test_zhihu_doc() -> None:
    assert "zhihu_title.txt" in DOC.read_text(encoding="utf-8")
