"""Round 62：封面裁剪与双比例预览。"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.cover_assets.crop_preview import (
    ASPECT_HORIZONTAL,
    ASPECT_SQUARE,
    build_dual_cover_previews,
    crop_for_aspect,
    crop_focal_point,
    enrich_cover_config,
    normalize_crop_dict,
    pillow_available,
    probe_image_size,
    square_crop_from_focal,
)
from wechat_article_scheduler.web.covers import normalize_cover_config
from tests.conftest import make_test_config


def _write_png(path: Path, w: int, h: int) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        n = len(data)
        return struct.pack(">I", n) + tag + data + struct.pack(">I", 0)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    row = b"\x00" + b"".join(b"\x00\xff\x00" for _ in range(w))
    raw = row * h
    import zlib

    idat = zlib.compress(raw)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def test_normalize_crop_and_focal() -> None:
    crop = normalize_crop_dict({"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.3})
    focal = crop_focal_point(crop)
    assert abs(focal["x"] - 0.35) < 0.001
    assert abs(focal["y"] - 0.35) < 0.001


def test_square_crop_from_focal() -> None:
    sq = square_crop_from_focal(1000, 800, {"x": 0.5, "y": 0.5})
    assert abs(sq["width"] * 1000 - sq["height"] * 800) < 2


def test_crop_for_aspect_horizontal_vs_square() -> None:
    crop = {"x": 0.0, "y": 0.1, "width": 1.0, "height": 0.4}
    h = crop_for_aspect(2350, 1000, crop=crop, aspect=ASPECT_HORIZONTAL)
    s = crop_for_aspect(2350, 1000, crop=crop, aspect=ASPECT_SQUARE)
    assert abs(h["width"] - 1.0) < 0.01
    assert s["width"] > 0 and s["height"] > 0
    assert s["width"] != h["height"] or s["height"] != h["height"]


def test_probe_image_size_without_pillow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wechat_article_scheduler.cover_assets.crop_preview.pillow_available",
        lambda: False,
    )
    png = tmp_path / "t.png"
    _write_png(png, 120, 80)
    assert probe_image_size(png) == (120, 80)


def test_build_dual_previews_css_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wechat_article_scheduler.cover_assets.crop_preview.pillow_available",
        lambda: False,
    )
    png = tmp_path / "cover.png"
    _write_png(png, 400, 300)
    cfg = normalize_cover_config({"crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.5}})
    out = build_dual_cover_previews(png, cfg)
    assert out["ok"] is True
    assert out["horizontal"]["render_mode"] == "css"
    assert out["square"]["render_mode"] == "css"
    assert out["horizontal"]["css"]["background_size"]


def test_build_dual_previews_with_pillow_when_available(tmp_path: Path) -> None:
    if not pillow_available():
        pytest.skip("Pillow 未安装")
    from PIL import Image

    png = tmp_path / "cover.jpg"
    Image.new("RGB", (320, 200), color=(40, 120, 200)).save(png, format="JPEG")
    cfg = normalize_cover_config({"crop": {"x": 0, "y": 0, "width": 1, "height": 0.5}})
    out = build_dual_cover_previews(png, cfg)
    assert out["ok"] is True
    assert out["horizontal"]["render_mode"] == "jpeg"
    assert out["horizontal"]["image_base64"]


def test_enrich_cover_config_adds_focal() -> None:
    data = enrich_cover_config({"crop": {"x": 0, "y": 0, "width": 0.5, "height": 0.5}})
    assert "focal" in data


@pytest.fixture
def app_config(tmp_path: Path):
    db_path = tmp_path / "crop.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def test_article_cover_previews_api(app_config, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient
    from wechat_article_scheduler.web import create_app

    app_config.covers_dir.mkdir(parents=True, exist_ok=True)
    cover = app_config.covers_dir / "art.jpg"
    _write_png(cover, 200, 100)
    cfg = normalize_cover_config({"crop": {"x": 0, "y": 0.1, "width": 1, "height": 0.6}})
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path, cover_config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("/tmp/a.md", "A", "", "", "h", "imported", str(cover), cfg),
        )
        conn.commit()
        aid = conn.execute("SELECT id FROM articles").fetchone()[0]
    client = TestClient(create_app(app_config))
    r = client.get(f"/api/articles/{aid}/cover-previews")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "horizontal" in body and "square" in body
