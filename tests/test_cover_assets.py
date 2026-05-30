from pathlib import Path

from wechat_article_scheduler.cover_assets import (
    check_cover_path,
    index_cover_directory,
)


def test_index_cover_directory(tmp_path: Path) -> None:
    root = tmp_path / "cover_assets"
    root.mkdir()
    (root / "a.png").write_bytes(b"\x89PNG")
    (root / "readme.txt").write_text("x", encoding="utf-8")
    assets = index_cover_directory(root)
    assert len(assets) == 1
    assert assets[0].name == "a.png"


def test_check_cover_path_missing_uses_default(tmp_path: Path) -> None:
    default = tmp_path / "default.png"
    default.write_bytes(b"x")
    result = check_cover_path(None, default_thumb=default)
    assert result["ok"] is True
    assert result["using_default"] is True


def test_check_cover_path_invalid() -> None:
    result = check_cover_path(Path("/no/such/cover.png"))
    assert result["ok"] is False
