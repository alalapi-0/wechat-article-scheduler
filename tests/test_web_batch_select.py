"""作品库批量选择与批量封面（Round 52+）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.covers import normalize_cover_config
from tests.conftest import make_test_config

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "batch.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg)), cfg


def _upload_two_articles(client: TestClient) -> list[int]:
    c, _cfg = client
    c.post(
        "/api/upload",
        files=[
            ("articles", ("a.md", b"# A\n\none", "text/markdown")),
            ("articles", ("b.md", b"# B\n\ntwo", "text/markdown")),
        ],
    )
    return [a["id"] for a in c.get("/api/articles").json()]


def test_index_has_batch_selection_ui(client: TestClient) -> None:
    c, _cfg = client
    html = c.get("/").text
    assert "全选" in html
    assert "批量设置封面" in html
    assert "worksMarquee" in html
    assert "coverBatchBack" in html


def test_normalize_cover_config() -> None:
    raw = normalize_cover_config({"crop": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.6}})
    assert json.loads(raw)["crop"]["width"] == 0.8


def test_batch_cover_upload_applies_to_selected(client: TestClient) -> None:
    c, cfg = client
    ids = _upload_two_articles(client)
    r = c.post(
        "/api/articles/batch-cover",
        data={"ids": json.dumps(ids)},
        files={"cover": ("batch.png", PNG, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["updated"] == 2
    arts = {a["id"]: a for a in c.get("/api/articles").json()}
    assert all(arts[i]["has_cover"] for i in ids)
    with db.connect(cfg.database_path) as conn:
        paths = {
            row[0]
            for row in conn.execute(
                "SELECT cover_path FROM articles WHERE id IN (?, ?)", tuple(ids)
            ).fetchall()
        }
    assert len(paths) == 1


def test_batch_cover_reuses_config_from_source(client: TestClient) -> None:
    c, cfg = client
    ids = _upload_two_articles(client)
    source_id, target_id = ids[0], ids[1]
    cfg_json = normalize_cover_config({"crop": {"x": 0, "y": 0, "width": 1, "height": 0.5}})
    c.post(
        f"/api/articles/{source_id}/cover",
        data={"cover_config_json": cfg_json},
        files={"cover": ("src.png", PNG, "image/png")},
    )
    r = c.post(
        "/api/articles/batch-cover",
        data={
            "ids": json.dumps([target_id]),
            "copy_from_article_id": str(source_id),
            "reuse_config_from_article_id": str(source_id),
        },
    )
    assert r.status_code == 200
    with db.connect(cfg.database_path) as conn:
        row = conn.execute(
            "SELECT cover_path, cover_config_json FROM articles WHERE id = ?",
            (target_id,),
        ).fetchone()
        src = conn.execute(
            "SELECT cover_path, cover_config_json FROM articles WHERE id = ?",
            (source_id,),
        ).fetchone()
    assert row["cover_path"] == src["cover_path"]
    assert row["cover_config_json"] == cfg_json


def test_batch_cover_from_asset_path(client: TestClient, tmp_path: Path) -> None:
    c, cfg = client
    ids = _upload_two_articles(client)
    asset = cfg.root / "cover_assets"
    asset.mkdir(parents=True, exist_ok=True)
    asset_file = asset / "lib.png"
    asset_file.write_bytes(PNG)
    r = c.post(
        "/api/articles/batch-cover",
        data={
            "ids": json.dumps(ids),
            "cover_asset_path": str(asset_file),
        },
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 2


def test_batch_cover_skips_missing_articles(client: TestClient) -> None:
    c, _cfg = client
    ids = _upload_two_articles(client)
    r = c.post(
        "/api/articles/batch-cover",
        data={"ids": json.dumps([ids[0], 99999])},
        files={"cover": ("x.png", PNG, "image/png")},
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    assert r.json()["skipped"] == 1


def test_single_cover_accepts_cover_config(client: TestClient) -> None:
    c, cfg = client
    aid = _upload_two_articles(client)[0]
    cfg_json = normalize_cover_config({"crop": {"x": 0.2, "y": 0.2, "width": 0.5, "height": 0.5}})
    assert c.post(
        f"/api/articles/{aid}/cover",
        data={"cover_config_json": cfg_json},
        files={"cover": ("one.png", PNG, "image/png")},
    ).status_code == 200
    art = next(a for a in c.get("/api/articles").json() if a["id"] == aid)
    assert art["has_cover_config"] is True
