from pathlib import Path

import pytest

from wechat_article_scheduler.cover_assets import (
    check_cover_path,
    index_cover_directory,
)
from wechat_article_scheduler.cover_assets.index import InvalidCoverError, MAX_COVER_BYTES, secure_cover_bytes
from tests.test_web_upload import PNG


def test_index_cover_directory(tmp_path: Path) -> None:
    root = tmp_path / "cover_assets"
    root.mkdir()
    (root / "a.png").write_bytes(PNG)
    (root / "old.gif").write_bytes(b"GIF89a")
    (root / "old.webp").write_bytes(b"RIFF")
    (root / "readme.txt").write_text("x", encoding="utf-8")
    assets = index_cover_directory(root)
    assert len(assets) == 1
    assert assets[0].name == "a.png"


def test_index_cover_directory_uses_safe_descriptor_listing(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "cover_assets"
    root.mkdir()
    (root / "a.png").write_bytes(PNG)
    monkeypatch.setattr(Path, "iterdir", lambda _path: (_ for _ in ()).throw(AssertionError("iterdir")))
    assert [asset.name for asset in index_cover_directory(root)] == ["a.png"]

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret-name.png").write_bytes(PNG)
    linked = tmp_path / "linked-covers"
    linked.symlink_to(outside, target_is_directory=True)
    assert index_cover_directory(linked) == []


def test_cover_index_reads_original_directory_after_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    root = tmp_path / "cover_assets"
    detached = tmp_path / "detached-covers"
    root.mkdir()
    (root / "a.png").write_bytes(PNG)
    original_list = fs.DirectoryHandle.list_names
    swapped = {"done": False}

    def list_then_replace(handle):
        names = original_list(handle)
        if handle.path == root.absolute() and not swapped["done"]:
            swapped["done"] = True
            root.rename(detached)
            root.mkdir()
            (root / "a.png").write_bytes(b"replacement-not-an-image")
        return names

    monkeypatch.setattr(fs.DirectoryHandle, "list_names", list_then_replace)
    assert [asset.name for asset in index_cover_directory(root)] == ["a.png"]
    assert (root / "a.png").read_bytes() == b"replacement-not-an-image"


def test_check_cover_path_missing_uses_default(tmp_path: Path) -> None:
    default = tmp_path / "default.png"
    default.write_bytes(PNG)
    result = check_cover_path(None, default_thumb=default)
    assert result["ok"] is True
    assert result["using_default"] is True


def test_check_cover_path_invalid() -> None:
    result = check_cover_path(Path("/no/such/cover.png"))
    assert result["ok"] is False


def test_check_cover_path_rejects_unsupported_image_type(tmp_path: Path) -> None:
    cover = tmp_path / "legacy.gif"
    cover.write_bytes(b"GIF89a")
    result = check_cover_path(cover)
    assert result["ok"] is False
    assert result["reason"] == "unsupported_type"


def test_oversized_cover_file_is_rejected_before_descriptor_read(
    tmp_path: Path, monkeypatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    cover = tmp_path / "oversized.png"
    with cover.open("wb") as stream:
        stream.truncate(MAX_COVER_BYTES + 1)
    monkeypatch.setattr(fs.os, "read", lambda *_args: (_ for _ in ()).throw(AssertionError("read")))
    with pytest.raises(InvalidCoverError, match="超过允许大小"):
        secure_cover_bytes(cover, allowed_roots=(tmp_path,))
    assert index_cover_directory(tmp_path) == []
