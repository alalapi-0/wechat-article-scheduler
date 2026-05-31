"""网页批量上传作品与封面（Round 44）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

# 最小合法 1x1 PNG
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "u.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg)), cfg


def test_upload_articles_and_covers_match_by_name(client) -> None:
    c, cfg = client
    files = [
        ("articles", ("chapter1.md", b"# Ch1\n\nbody one", "text/markdown")),
        ("articles", ("chapter2.md", b"# Ch2\n\nbody two", "text/markdown")),
        ("covers", ("chapter1.png", PNG, "image/png")),
    ]
    r = c.post("/api/upload", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["saved_articles"] == 2
    assert data["saved_covers"] == 1
    assert data["scan"]["imported"] == 2
    assert data["matched_covers"] == 1

    arts = {a["title"]: a for a in c.get("/api/articles").json()}
    ch1 = next(a for a in arts.values() if "Ch1" in a["title"])
    assert ch1["has_cover"] is True
    assert ch1["cover_url"] == f"/media/cover/{ch1['id']}"
    img = c.get(f"/media/cover/{ch1['id']}")
    assert img.status_code == 200


def test_upload_rejects_unsupported_extensions(client) -> None:
    c, cfg = client
    files = [
        ("articles", ("evil.exe", b"x", "application/octet-stream")),
        ("covers", ("note.txt", b"x", "text/plain")),
    ]
    data = c.post("/api/upload", files=files).json()
    assert data["saved_articles"] == 0
    assert data["saved_covers"] == 0
    assert data["skipped_articles"]
    assert data["skipped_covers"]


def test_set_article_cover_endpoint(client) -> None:
    c, cfg = client
    c.post("/api/upload", files=[("articles", ("solo.md", b"# Solo\n\nbody", "text/markdown"))])
    aid = c.get("/api/articles").json()[0]["id"]
    r = c.post(f"/api/articles/{aid}/cover", files={"cover": ("new.png", PNG, "image/png")})
    assert r.status_code == 200
    assert c.get("/api/articles").json()[0]["has_cover"] is True
    assert c.get(f"/media/cover/{aid}").status_code == 200


def test_uploaded_article_plans_and_keeps_cover(client) -> None:
    c, cfg = client
    c.post(
        "/api/upload",
        files=[
            ("articles", ("p.md", b"# P\n\nbody", "text/markdown")),
            ("covers", ("p.png", PNG, "image/png")),
        ],
    )
    plan = c.post("/api/plan").json()
    assert plan["planned"] == 1
    with db.connect(cfg.database_path) as conn:
        cover = conn.execute("SELECT cover_path FROM articles LIMIT 1").fetchone()[0]
    assert cover and Path(cover).is_file()


def test_empty_upload_returns_hint(client) -> None:
    from wechat_article_scheduler.web.uploads import handle_upload

    _c, cfg = client
    data = handle_upload(cfg, articles=[], covers=[])
    assert data["saved_articles"] == 0
    assert data["saved_covers"] == 0
    assert any("没有可处理" in line for line in data["human"])
