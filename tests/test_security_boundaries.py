"""Focused offline regression tests for local security boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
import os
import sqlite3
import struct
import time
import zlib

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_test_config
from tests.test_web_upload import PNG
from wechat_article_scheduler import db
from PIL import Image, PngImagePlugin
from wechat_article_scheduler.cover_assets import InvalidCoverError, managed_cover_bytes
from wechat_article_scheduler.cover_assets.index import validate_image_bytes
from wechat_article_scheduler.draft_update import draft_content_fingerprint
from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.external_agent.redaction import (
    assert_no_sensitive_values,
    redact_text,
)
from wechat_article_scheduler.preview_snapshot import _snapshot_html_document
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.scan_preflight import build_scan_preflight
from wechat_article_scheduler.filesystem_safety import (
    open_directory_handle,
    read_regular_file,
    unlink_if_unchanged,
)
from wechat_article_scheduler.filesystem_safety import UnsafePathError, write_new_file
from wechat_article_scheduler.content_library.collection_scan import _scan_directory
from wechat_article_scheduler.web.trash import purge_trash


def _client(tmp_path: Path):
    cfg = make_test_config(tmp_path, tmp_path / "security.sqlite3")
    db.init_db(cfg.database_path)
    return TestClient(create_app(cfg)), cfg


@pytest.mark.parametrize(
    "headers,status",
    [
        ({"host": "attacker.example"}, 400),
        ({"origin": "https://attacker.example"}, 403),
        ({"referer": "http://testserver.evil/form"}, 403),
        ({"origin": "http://testserver:81"}, 403),
    ],
)
def test_state_change_rejects_nonlocal_request_before_mutation(tmp_path: Path, headers, status) -> None:
    client, cfg = _client(tmp_path)
    response = client.post(
        "/api/upload",
        headers=headers,
        files=[("articles", ("bad.md", b"# bad\n\nbody", "text/markdown"))],
    )
    assert response.status_code == status
    with db.connect(cfg.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0


def test_hostile_host_rejects_get_before_database_access(tmp_path: Path, monkeypatch) -> None:
    client, _cfg = _client(tmp_path)
    monkeypatch.setattr(
        "wechat_article_scheduler.web.app.db.connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("database read")),
    )
    assert client.get("/api/articles", headers={"host": "attacker.example"}).status_code == 400


def test_all_numeric_loopbacks_allowed_but_duplicate_host_and_cross_site_rejected(tmp_path: Path) -> None:
    client, _cfg = _client(tmp_path)
    assert client.get("/api/status", headers={"host": "127.0.0.2"}).status_code == 200
    duplicate = client.get("/api/status", headers=[("host", "localhost"), ("host", "attacker")])
    assert duplicate.status_code == 400
    cross_site = client.post(
        "/api/upload",
        headers={"sec-fetch-site": "cross-site"},
        files=[("articles", ("bad.md", b"# bad\n\nbody", "text/markdown"))],
    )
    assert cross_site.status_code == 403


@pytest.mark.parametrize(
    "headers",
    [
        {"origin": "http://testserver"},
        {"referer": "http://testserver/workbench/form?from=local"},
    ],
)
def test_same_origin_browser_mutation_headers_are_accepted(tmp_path: Path, headers: dict[str, str]) -> None:
    client, _cfg = _client(tmp_path)
    response = client.post("/api/articles/delete-preview", headers=headers, json={"ids": []})
    assert response.status_code == 200


def test_origin_with_path_is_rejected(tmp_path: Path) -> None:
    client, _cfg = _client(tmp_path)
    response = client.post(
        "/api/articles/delete-preview",
        headers={"origin": "http://testserver/not-an-origin"},
        json={"ids": []},
    )
    assert response.status_code == 403


def test_scan_preflight_get_is_read_only(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "readonly.sqlite3")
    assert not cfg.inbox_dir.exists()
    report = build_scan_preflight(cfg)
    assert report["inbox_exists"] is False
    assert not cfg.inbox_dir.exists()


def test_scan_preflight_rejects_symlinked_intermediate_directory(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "readonly.sqlite3")
    outside = tmp_path / "outside"
    outside.mkdir()
    articles = tmp_path / "articles"
    articles.symlink_to(outside, target_is_directory=True)
    report = build_scan_preflight(cfg)
    assert report["blocked"] is True


def test_configured_inbox_outside_project_root_uses_its_own_managed_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    inbox = tmp_path / "runtime" / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "entry.md").write_text("# External inbox\n\nBody", encoding="utf-8")
    cfg = make_test_config(tmp_path, tmp_path / "external-inbox.sqlite3")
    cfg.root = project_root
    cfg.inbox_dir = inbox
    db.init_db(cfg.database_path)

    assert build_scan_preflight(cfg)["ready"] is True
    result = scan_inbox(cfg)

    assert result["imported"] == 1
    assert not (inbox / "entry.md").exists()
    assert (inbox.parent / "imported" / "entry.md").is_file()


def test_collection_scan_rejects_parent_symlink_before_listing_or_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "collection.sqlite3")
    db.init_db(cfg.database_path)
    outside = tmp_path / "outside"
    (outside / "inbox").mkdir(parents=True)
    (outside / "inbox" / "secret-name.md").write_text("# outside", encoding="utf-8")
    (tmp_path / "articles").symlink_to(outside, target_is_directory=True)
    original_iterdir = Path.iterdir

    def reject_outside_listing(path: Path):
        if path == cfg.inbox_dir:
            raise AssertionError("unsafe inbox was listed")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", reject_outside_listing)
    with db.connect(cfg.database_path) as conn:
        result = _scan_directory(
            cfg,
            conn,
            inbox=cfg.inbox_dir,
            collection_id=1,
            coll_cfg=None,
            imported_dir=cfg.imported_dir,
            exts={".md"},
            summary_max=120,
            rules=cfg.rules,
        )
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    assert result["scanned"] == result["imported"] == result["errors"] == 0


def test_collection_scan_parses_and_moves_from_original_held_inbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs
    from wechat_article_scheduler.content_library.repository import ensure_default_collection

    cfg = make_test_config(tmp_path, tmp_path / "held-scan.sqlite3")
    db.init_db(cfg.database_path)
    inbox = cfg.inbox_dir
    detached = inbox.parent / "detached-inbox"
    inbox.mkdir(parents=True)
    (inbox / "entry.md").write_text("# Original\n\noriginal-body", encoding="utf-8")
    original_list = fs.DirectoryHandle.list_names
    swapped = {"done": False}

    def list_then_replace(handle):
        names = original_list(handle)
        if handle.path == inbox.absolute() and not swapped["done"]:
            swapped["done"] = True
            inbox.rename(detached)
            inbox.mkdir()
            (inbox / "entry.md").write_text(
                "# Replacement\n\nreplacement-must-not-be-read", encoding="utf-8"
            )
        return names

    monkeypatch.setattr(fs.DirectoryHandle, "list_names", list_then_replace)
    with db.connect(cfg.database_path) as conn:
        collection_id = ensure_default_collection(conn)
        result = _scan_directory(
            cfg,
            conn,
            inbox=inbox,
            collection_id=collection_id,
            coll_cfg=None,
            imported_dir=cfg.imported_dir,
            exts={".md"},
            summary_max=120,
            rules=cfg.rules,
        )
        row = conn.execute("SELECT title, body FROM articles").fetchone()
    assert result["imported"] == 1
    assert row["title"] == "Original"
    assert "replacement-must-not-be-read" not in row["body"]
    assert not (detached / "entry.md").exists()
    assert "replacement-must-not-be-read" in (inbox / "entry.md").read_text(encoding="utf-8")


def test_invalid_and_aliased_covers_are_never_managed(tmp_path: Path) -> None:
    _client_obj, cfg = _client(tmp_path)
    cfg.covers_dir.mkdir(parents=True, exist_ok=True)
    invalid = cfg.covers_dir / "renamed.png"
    invalid.write_bytes(b"not an image")
    with pytest.raises(InvalidCoverError):
        managed_cover_bytes(cfg, invalid)

    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG)
    symlink = cfg.covers_dir / "linked.png"
    symlink.symlink_to(outside)
    with pytest.raises(InvalidCoverError):
        managed_cover_bytes(cfg, symlink)

    original = cfg.covers_dir / "original.png"
    original.write_bytes(PNG)
    alias = cfg.covers_dir / "alias.png"
    alias.hardlink_to(original)
    with pytest.raises(InvalidCoverError):
        managed_cover_bytes(cfg, original)
    with pytest.raises(InvalidCoverError):
        managed_cover_bytes(cfg, alias)


def test_redaction_covers_password_api_key_and_multiline_private_key() -> None:
    raw = (
        "PASSWORD=hunter2\nAPI_KEY: abc123\n"
        "PEM=-----BEGIN PRIVATE KEY-----\nsecret-lines\n-----END PRIVATE KEY-----"
    )
    redacted = redact_text(raw)
    assert "hunter2" not in redacted
    assert "abc123" not in redacted
    assert "secret-lines" not in redacted
    assert "BEGIN PRIVATE KEY" not in redacted


def test_redaction_normalizes_separator_variants_and_generic_pem() -> None:
    raw = (
        '"api-key": "one"\napi.key=two\napi key: three\nMY_PASSWORD=four\n'
        "-----BEGIN CERTIFICATE-----\nfive\n-----END CERTIFICATE-----"
    )
    redacted = redact_text(raw)
    for secret in ("one", "two", "three", "four", "five", "BEGIN CERTIFICATE"):
        assert secret not in redacted


def test_redaction_covers_split_password_names_and_unterminated_pem() -> None:
    redacted = redact_text(
        "PASS-WORD=one\nPASS WD=two\n-----BEGIN PRIVATE KEY-----\nthree\nfour"
    )
    assert all(secret not in redacted for secret in ("one", "two", "three", "four", "BEGIN"))


def test_redaction_covers_generic_credential_key_variants_and_assertion_is_independent() -> None:
    raw = (
        "SECRET=one\ntoken: two\nClient.Secret=three\nACCESS-TOKEN=four\n"
        "refresh token: five\nSession-ID=six\nCOOKIE_VALUE=seven\n"
        "Authorization: Bearer eight\nbearer=nine\nordinary prose stays useful"
    )
    redacted = redact_text(raw)
    assert all(secret not in redacted for secret in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine"))
    assert "ordinary prose stays useful" in redacted
    assert_no_sensitive_values(redacted)
    with pytest.raises(ValueError, match="sensitive-looking"):
        assert_no_sensitive_values("client_secret: assertion-catches-this")


def test_redaction_covers_exact_generic_auth_key_and_credential_assignments() -> None:
    raw = (
        "auth=abc123\nauthentication: def456\nkey=ghi789\n"
        "client_key=jkl012\nsigning-key: mno345\nprivate.key=pqr678\n"
        "access key: stu901\ncredentials=vw2345\napiKey=yz6789\n"
        "client_auth=compound-auth\nauth_key=compound-key"
    )
    redacted = redact_text(raw)
    for secret in (
        "abc123", "def456", "ghi789", "jkl012", "mno345",
        "pqr678", "stu901", "vw2345", "yz6789", "compound-auth", "compound-key",
    ):
        assert secret not in redacted
    assert_no_sensitive_values(redacted)
    for leaked in (
        "auth=abc123",
        "authentication=abc123",
        "key=abc123",
        "credentials=abc123",
        "client_auth=four",
        "auth_key=five",
    ):
        with pytest.raises(ValueError, match="sensitive-looking"):
            assert_no_sensitive_values(leaked)


def test_redaction_preserves_non_secret_key_substrings_and_prose() -> None:
    raw = "monkey=curious\nkeyboard=mechanical\nturnkey=ready\nA monkey uses a keyboard."
    assert redact_text(raw) == raw
    assert_no_sensitive_values(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "mode=mock; SECRET=alpha",
        "url=https://local/?token=bravo",
        "ok=1&session_id=delta",
    ],
)
def test_redaction_assertion_detects_later_same_line_assignments(raw: str) -> None:
    with pytest.raises(ValueError, match="sensitive-looking"):
        assert_no_sensitive_values(raw)


def test_redaction_assertion_accepts_redacted_json_and_useful_prose() -> None:
    assert_no_sensitive_values(
        '{"mode":"mock","client_secret":"<redacted>",'
        '"token":"<redacted>","note":"token handling documentation"}'
    )
    assert_no_sensitive_values("ordinary prose about tokens and sessions stays useful")


@pytest.mark.parametrize("raw", ["PASSWORD=secret,tail", "PASSWORD=secret;tail"])
def test_redaction_consumes_entire_unquoted_secret_line(raw: str) -> None:
    redacted = redact_text(raw)
    assert "secret" not in redacted
    assert "tail" not in redacted


def test_snapshot_escapes_metadata_but_preserves_trusted_article_html() -> None:
    package = (
        {
            "title": "<script>title()</script>",
            "summary": "<img src=x onerror=summary()>",
            "approximation_note": "<b>note</b>",
            "content_hints": ["<i>hint</i>"],
            "html_body": "<p class=\"trusted\">article</p>",
        }
    )
    document = _snapshot_html_document(package, trusted_article_html=True)
    assert "<script>" not in document
    assert "<img" not in document
    assert "<b>note</b>" not in document
    assert '<p class="trusted">article</p>' in document
    assert '&lt;p class=&quot;trusted&quot;&gt;article&lt;/p&gt;' in _snapshot_html_document(package)


def test_save_snapshot_never_trusts_caller_supplied_html_body(tmp_path: Path) -> None:
    from wechat_article_scheduler.preview_snapshot import save_preview_snapshot

    cfg = make_test_config(tmp_path, tmp_path / "malicious-snapshot.sqlite3")
    saved = save_preview_snapshot(
        cfg,
        {
            "article_id": 7,
            "title": "safe",
            "summary": "",
            "raw_body": "<script>alert('raw')</script><p>body</p>",
            "html_body": "<script>alert('forged')</script>",
        },
    )
    html = saved.with_suffix(".html").read_text(encoding="utf-8")
    assert "<script" not in html.lower()
    assert "forged" not in html


def test_png_trailing_bytes_rejected_and_metadata_removed(tmp_path: Path) -> None:
    with pytest.raises(InvalidCoverError):
        validate_image_bytes(PNG + b"PASSWORD=hunter2", ".png")
    path = tmp_path / "articles" / "covers" / "meta.png"
    path.parent.mkdir(parents=True)
    info = PngImagePlugin.PngInfo()
    info.add_text("note", "PASSWORD=hunter2")
    Image.new("RGB", (2, 2), "red").save(path, format="PNG", pnginfo=info)
    payload = managed_cover_bytes(make_test_config(tmp_path, tmp_path / "x.sqlite3"), path)
    assert b"hunter2" not in payload
    assert b"PASSWORD" not in payload


def test_png_compressed_bomb_is_rejected_by_exact_bounded_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    bomb = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" * (8 * 1024 * 1024), level=9))
        + chunk(b"IEND", b"")
    )

    def unbounded_decompress_forbidden(*_args, **_kwargs):
        raise AssertionError("unbounded zlib.decompress must never be called")

    monkeypatch.setattr(zlib, "decompress", unbounded_decompress_forbidden)
    with pytest.raises(InvalidCoverError):
        validate_image_bytes(bomb, ".png")


def test_png_stream_rejects_truncation_concatenation_and_oversized_dimensions() -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\x00\x00"
    invalid_streams = (
        zlib.compress(raw)[:-1],
        zlib.compress(raw) + zlib.compress(b"trailing-stream"),
        zlib.compress(raw + b"extra-expanded-output"),
    )
    for compressed in invalid_streams:
        candidate = signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
        with pytest.raises(InvalidCoverError):
            validate_image_bytes(candidate, ".png")

    oversized_ihdr = struct.pack(">IIBBBBB", 16_385, 1, 8, 2, 0, 0, 0)
    oversized = (
        signature
        + chunk(b"IHDR", oversized_ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    with pytest.raises(InvalidCoverError):
        validate_image_bytes(oversized, ".png")


def test_png_bounded_stream_accepts_valid_adam7_image() -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    width = height = 8
    raw = bytearray()
    for start_x, start_y, step_x, step_y in (
        (0, 0, 8, 8),
        (4, 0, 8, 8),
        (0, 4, 4, 8),
        (2, 0, 4, 4),
        (0, 2, 2, 4),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    ):
        pass_width = (width - start_x + step_x - 1) // step_x
        pass_height = (height - start_y + step_y - 1) // step_y
        for _ in range(pass_height):
            raw.extend(b"\x00" + b"\x7f\x20\xe0" * pass_width)
    candidate = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 1))
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )
    assert validate_image_bytes(candidate, ".png") == "png"
    with Image.open(BytesIO(candidate)) as image:
        image.load()
        assert image.size == (8, 8)


def test_png_rejects_excessive_input_and_idat_chunk_work() -> None:
    from wechat_article_scheduler.cover_assets.index import MAX_COVER_BYTES

    with pytest.raises(InvalidCoverError, match="不能超过"):
        validate_image_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * MAX_COVER_BYTES, ".png")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    candidate = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + b"".join(chunk(b"IDAT", b"") for _ in range(1025))
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + chunk(b"IEND", b"")
    )
    with pytest.raises(InvalidCoverError):
        validate_image_bytes(candidate, ".png")


def test_unlink_rejects_same_inode_content_change(tmp_path: Path) -> None:
    path = tmp_path / "owned.txt"
    path.write_bytes(b"before")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    path.write_bytes(b"after")
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"after"


def test_unlink_rejects_directory_entry_swap(tmp_path: Path) -> None:
    path = tmp_path / "owned.txt"
    replacement = tmp_path / "replacement.txt"
    path.write_bytes(b"before")
    replacement.write_bytes(b"replacement")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    path.unlink()
    replacement.rename(path)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"replacement"


@pytest.mark.parametrize("mode", [0o720, 0o702])
def test_unlink_refuses_writable_parent_before_target_open_or_mutation(
    tmp_path: Path, mode: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    parent = tmp_path / "managed"
    parent.mkdir(mode=0o700)
    path = parent / "owned.txt"
    path.write_bytes(b"keep")
    snapshot = read_regular_file(path, allowed_roots=(parent,))
    parent.chmod(mode)
    original_open = fs.os.open
    target_opened = False

    def tracked_open(name, flags, *args, dir_fd=None, **kwargs):
        nonlocal target_opened
        if name == path.name and dir_fd is not None:
            target_opened = True
        return original_open(name, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(fs.os, "open", tracked_open)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(parent,)) is False
    assert target_opened is False
    assert path.read_bytes() == b"keep"
    assert not (parent / fs._QUARANTINE_DIRECTORY).exists()


def test_unlink_initial_fifo_returns_quickly_without_mutation(tmp_path: Path) -> None:
    from wechat_article_scheduler.filesystem_safety import FileSnapshot

    fifo = tmp_path / "untrusted"
    os.mkfifo(fifo)
    started = time.monotonic()
    assert unlink_if_unchanged(
        fifo,
        FileSnapshot(data=b"", device=-1, inode=-1),
        allowed_roots=(tmp_path,),
    ) is False
    assert time.monotonic() - started < 1
    assert fifo.exists()


@pytest.mark.parametrize("replacement_kind", ["directory", "fifo"])
def test_unlink_preopen_substitution_never_hangs_or_hides_entry(
    tmp_path: Path, replacement_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    displaced = tmp_path / "displaced.txt"
    path.write_bytes(b"original")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original_open = fs.os.open
    injected = False

    def substitute_then_open(name, flags, *args, dir_fd=None, **kwargs):
        nonlocal injected
        if name == path.name and dir_fd is not None and not injected:
            injected = True
            path.rename(displaced)
            if replacement_kind == "directory":
                path.mkdir()
            else:
                os.mkfifo(path)
        return original_open(name, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(fs.os, "open", substitute_then_open)
    started = time.monotonic()
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert time.monotonic() - started < 1
    assert path.exists()
    assert displaced.read_bytes() == b"original"
    assert not (tmp_path / fs._QUARANTINE_DIRECTORY).exists()


def test_directory_listing_is_fd_scanned_and_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    monkeypatch.setattr(
        os,
        "listdir",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("listdir materialized")),
    )
    with open_directory_handle(tmp_path, allowed_roots=(tmp_path,)) as handle:
        with pytest.raises(UnsafePathError, match="数量超过"):
            handle.list_names(max_entries=2)


def test_held_directory_handle_ignores_replacement_and_unlinks_original_entry(
    tmp_path: Path,
) -> None:
    root = tmp_path / "managed"
    detached = tmp_path / "detached"
    root.mkdir()
    (root / "owned.txt").write_bytes(b"original")
    with open_directory_handle(root, allowed_roots=(root,)) as handle:
        assert handle.list_names() == ["owned.txt"]
        root.rename(detached)
        root.mkdir()
        replacement = root / "owned.txt"
        replacement.write_bytes(b"replacement-must-survive")
        snapshot = handle.read_regular_file("owned.txt")
        assert snapshot.data == b"original"
        assert handle.unlink_if_unchanged("owned.txt", snapshot) is True
    assert replacement.read_bytes() == b"replacement-must-survive"
    assert not (detached / "owned.txt").exists()


def test_unlink_quarantines_injected_final_entry_swap_without_deleting_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    replacement = tmp_path / "replacement.txt"
    displaced = tmp_path / "displaced-original.txt"
    path.write_bytes(b"verified-original")
    replacement.write_bytes(b"replacement-must-survive")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original_quarantine = fs._quarantine_entry

    def swap_then_quarantine(parent_fd: int, name: str):
        path.rename(displaced)
        replacement.rename(path)
        return original_quarantine(parent_fd, name)

    monkeypatch.setattr(fs, "_quarantine_entry", swap_then_quarantine)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"replacement-must-survive"
    assert displaced.read_bytes() == b"verified-original"


def test_unlink_fails_closed_if_quarantine_identity_is_swapped_at_disposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    replacement = tmp_path / "replacement.txt"
    displaced = tmp_path / "displaced-original.txt"
    path.write_bytes(b"verified-original")
    replacement.write_bytes(b"replacement-must-survive")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original_dispose = fs._unlink_verified_quarantine

    def swap_before_disposal(quarantine_fd, entry, moved_fd, expected):
        quarantine_dir = tmp_path / fs._QUARANTINE_DIRECTORY
        (quarantine_dir / entry).rename(displaced)
        replacement.rename(quarantine_dir / entry)
        return original_dispose(quarantine_fd, entry, moved_fd, expected)

    monkeypatch.setattr(fs, "_unlink_verified_quarantine", swap_before_disposal)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert replacement.exists() is False
    assert path.read_bytes() == b"replacement-must-survive"
    assert list((tmp_path / fs._QUARANTINE_DIRECTORY).iterdir()) == []
    assert displaced.read_bytes() == b"verified-original"


def test_unlink_disposes_verified_inode_while_descriptor_is_held(tmp_path: Path) -> None:
    path = tmp_path / "owned.txt"
    path.write_bytes(b"secret-to-delete")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is True
    assert not path.exists()
    from wechat_article_scheduler import filesystem_safety as fs

    assert list((tmp_path / fs._QUARANTINE_DIRECTORY).iterdir()) == []


def test_quarantine_rejects_create_to_open_directory_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    path.write_bytes(b"keep")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original_open = fs.os.open
    swapped = False

    def replace_before_open(name, flags, *args, dir_fd=None, **kwargs):
        nonlocal swapped
        if name == fs._QUARANTINE_DIRECTORY and dir_fd is not None and not swapped:
            swapped = True
            quarantine = tmp_path / fs._QUARANTINE_DIRECTORY
            quarantine.rename(tmp_path / "detached-quarantine")
            quarantine.mkdir(mode=0o700)
        return original_open(name, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(fs.os, "open", replace_before_open)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"keep"
    assert (tmp_path / fs._QUARANTINE_DIRECTORY).is_dir()


def test_quarantine_held_fd_survives_parent_name_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    path.write_bytes(b"delete")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original = fs._quarantine_entry

    def detach_after_open(parent_fd: int, name: str):
        result = original(parent_fd, name)
        quarantine = tmp_path / fs._QUARANTINE_DIRECTORY
        quarantine.rename(tmp_path / "detached-quarantine")
        quarantine.mkdir(mode=0o700)
        return result

    monkeypatch.setattr(fs, "_quarantine_entry", detach_after_open)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is True
    assert not path.exists()
    assert (tmp_path / fs._QUARANTINE_DIRECTORY).is_dir()
    assert list((tmp_path / "detached-quarantine").iterdir()) == []


def test_quarantine_collision_never_overwrites_existing_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from wechat_article_scheduler import filesystem_safety as fs

    quarantine = tmp_path / fs._QUARANTINE_DIRECTORY
    quarantine.mkdir(mode=0o700)
    collision = quarantine / "entry-collision"
    collision.write_bytes(b"must-survive")
    values = iter((SimpleNamespace(hex="collision"), SimpleNamespace(hex="fresh")))
    monkeypatch.setattr(fs.uuid, "uuid4", lambda: next(values))
    path = tmp_path / "owned.txt"
    path.write_bytes(b"delete")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is True
    assert collision.read_bytes() == b"must-survive"
    assert not (quarantine / "entry-fresh").exists()


def test_quarantine_rename_failure_closes_fd_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    path.write_bytes(b"keep")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    opened: list[int] = []
    original_open = fs._open_owned_quarantine

    def record_open(parent_fd: int) -> int:
        fd = original_open(parent_fd)
        opened.append(fd)
        return fd

    monkeypatch.setattr(fs, "_open_owned_quarantine", record_open)
    monkeypatch.setattr(fs.os, "rename", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("boom")))
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"keep"
    assert opened
    with pytest.raises(OSError):
        os.fstat(opened[0])


def test_quarantine_post_move_open_failure_restores_file_and_closes_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    path = tmp_path / "owned.txt"
    path.write_bytes(b"keep")
    snapshot = read_regular_file(path, allowed_roots=(tmp_path,))
    original_quarantine = fs._quarantine_entry
    original_open = fs.os.open
    quarantine_fds: list[int] = []

    def record_quarantine(parent_fd: int, name: str):
        qfd, entry = original_quarantine(parent_fd, name)
        quarantine_fds.append(qfd)
        return qfd, entry

    def fail_moved_open(name, flags, *args, dir_fd=None, **kwargs):
        if isinstance(name, str) and name.startswith("entry-") and dir_fd in quarantine_fds:
            raise OSError("injected moved-entry open failure")
        return original_open(name, flags, *args, dir_fd=dir_fd, **kwargs)

    monkeypatch.setattr(fs, "_quarantine_entry", record_quarantine)
    monkeypatch.setattr(fs.os, "open", fail_moved_open)
    assert unlink_if_unchanged(path, snapshot, allowed_roots=(tmp_path,)) is False
    assert path.read_bytes() == b"keep"
    assert quarantine_fds
    with pytest.raises(OSError):
        os.fstat(quarantine_fds[0])


def test_write_rejects_post_write_hardlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    original = fs._written_file_is_safe

    def alias_then_check(parent_fd: int, name: str, expected: bytes) -> bool:
        target = tmp_path / name
        alias = tmp_path / "alias.txt"
        if not alias.exists():
            alias.hardlink_to(target)
        return original(parent_fd, name, expected)

    monkeypatch.setattr(fs, "_written_file_is_safe", alias_then_check)
    with pytest.raises(UnsafePathError, match="别名"):
        write_new_file(tmp_path / "new.txt", b"secret", allowed_roots=(tmp_path,))
    assert not (tmp_path / "new.txt").exists()


def test_purge_preserves_source_referenced_by_another_article(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "shared.sqlite3")
    db.init_db(cfg.database_path)
    source = cfg.imported_dir / "shared.md"
    source.parent.mkdir(parents=True)
    source.write_text("shared", encoding="utf-8")
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status,deleted_at) "
            "VALUES (?,'old','','b','old','imported',datetime('now'))",
            (str(source),),
        )
        conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status) "
            "VALUES (?,'active','','b','active','imported')",
            (str(source),),
        )
        conn.commit()
        result = purge_trash(cfg, conn)
    assert result["purged"] == 1
    assert source.read_text(encoding="utf-8") == "shared"


def test_purge_preserves_source_that_is_another_article_cover(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "cross-field.sqlite3")
    db.init_db(cfg.database_path)
    shared = cfg.covers_dir / "shared.png"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(PNG)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status,deleted_at) "
            "VALUES (?,'old','','b','old-cross','imported',datetime('now'))",
            (str(shared),),
        )
        conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status,cover_path) "
            "VALUES ('active.md','active','','b','active-cross','imported',?)",
            (str(shared),),
        )
        conn.commit()
        result = purge_trash(cfg, conn)
    assert result["purged"] == 1
    assert shared.exists()


@pytest.mark.parametrize("field", ["source_path", "cover_path"])
def test_purge_preserves_global_default_referenced_through_trashed_article(
    tmp_path: Path, field: str
) -> None:
    shared = tmp_path / "articles" / "covers" / "global.png"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(PNG)
    cfg = make_test_config(
        tmp_path,
        tmp_path / f"global-{field}.sqlite3",
        wechat_default_thumb_path=str(shared),
    )
    db.init_db(cfg.database_path)
    source = str(shared) if field == "source_path" else "missing-source.md"
    cover = str(shared) if field == "cover_path" else ""
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status,cover_path,deleted_at) "
            "VALUES (?,'old','','b',?,'imported',?,datetime('now'))",
            (source, f"global-{field}", cover),
        )
        conn.commit()
        assert purge_trash(cfg, conn)["purged"] == 1
    assert shared.exists()


def test_purge_holds_write_lock_across_reference_check_and_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler.web import trash

    cfg = make_test_config(tmp_path, tmp_path / "purge-lock.sqlite3")
    db.init_db(cfg.database_path)
    source = cfg.imported_dir / "purge-owned.md"
    source.parent.mkdir(parents=True)
    source.write_text("owned", encoding="utf-8")
    with db.connect(cfg.database_path) as conn:
        article_id = int(
            conn.execute(
                "INSERT INTO articles(source_path,title,summary,body,content_hash,status,deleted_at) "
                "VALUES (?,'old','','b','purge-lock','imported',datetime('now'))",
                (str(source),),
            ).lastrowid
        )
        conn.commit()

    original_unlink = trash.safe_unlink
    observed_lock = {"value": False}

    def competing_reference_then_unlink(config, raw):
        other = sqlite3.connect(cfg.database_path, timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute(
                    "INSERT INTO articles(source_path,title,summary,body,content_hash,status) "
                    "VALUES (?,'competitor','','b','competing-ref','imported')",
                    (str(source),),
                )
                other.commit()
            observed_lock["value"] = True
        finally:
            other.close()
        return original_unlink(config, raw)

    monkeypatch.setattr(trash, "safe_unlink", competing_reference_then_unlink)
    with db.connect(cfg.database_path) as conn:
        result = trash.purge_trash(cfg, conn)
        assert conn.in_transaction is True
        assert conn.execute("SELECT COUNT(*) FROM articles WHERE id=?", (article_id,)).fetchone()[0] == 0
        conn.commit()
        assert conn.in_transaction is False

    assert observed_lock["value"] is True
    assert result["purged"] == 1
    assert not source.exists()


def test_orphan_cleanup_rechecks_reference_after_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler.cover_assets import manager
    from wechat_article_scheduler.web.trash import safe_unlink

    cfg = make_test_config(tmp_path, tmp_path / "orphan.sqlite3")
    db.init_db(cfg.database_path)
    cover = cfg.covers_dir / "orphan.png"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(PNG)
    with db.connect(cfg.database_path) as conn:
        original = manager.referenced_cover_identities
        calls = {"count": 0}

        def reference_on_recheck(config, active_conn):
            calls["count"] += 1
            if calls["count"] == 2:
                active_conn.execute(
                    "INSERT INTO articles(source_path,title,summary,body,content_hash,status,cover_path) "
                    "VALUES ('x.md','t','','b','h','imported',?)",
                    (str(cover),),
                )
            return original(config, active_conn)

        monkeypatch.setattr(manager, "referenced_cover_identities", reference_on_recheck)
        result = manager.cleanup_orphan_covers(cfg, conn, unlink=safe_unlink)
    assert result["removed"] == 0
    assert cover.exists()


def test_orphan_cleanup_holds_database_write_lock_through_unlink(tmp_path: Path) -> None:
    from wechat_article_scheduler.cover_assets import manager
    from wechat_article_scheduler.web.trash import safe_unlink

    cfg = make_test_config(tmp_path, tmp_path / "orphan-lock.sqlite3")
    db.init_db(cfg.database_path)
    cover = cfg.covers_dir / "locked-orphan.png"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(PNG)
    observed_lock = {"value": False}

    def competing_reference_then_unlink(config, raw, **kwargs):
        other = sqlite3.connect(cfg.database_path, timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute(
                    "INSERT INTO articles(source_path,title,summary,body,content_hash,status,cover_path) "
                    "VALUES ('other.md','other','','b','other-lock','imported',?)",
                    (str(cover),),
                )
                other.commit()
            observed_lock["value"] = True
        finally:
            other.close()
        return safe_unlink(config, raw, **kwargs)

    with db.connect(cfg.database_path) as conn:
        result = manager.cleanup_orphan_covers(cfg, conn, unlink=competing_reference_then_unlink)
        conn.commit()
    assert observed_lock["value"] is True
    assert result["removed"] == 1
    assert not cover.exists()


def test_fingerprint_changes_when_cover_bytes_change(tmp_path: Path) -> None:
    cover = tmp_path / "articles" / "covers" / "cover.png"
    cover.parent.mkdir(parents=True, exist_ok=True)
    cover.write_bytes(PNG)
    cfg = make_test_config(tmp_path, tmp_path / "fp.sqlite3")
    first = draft_content_fingerprint(title="t", summary="s", body="b", cover_path=str(cover), config=cfg)
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    changed = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\xff\x00"))
        + chunk(b"IEND", b"")
    )
    cover.write_bytes(changed)
    second = draft_content_fingerprint(title="t", summary="s", body="b", cover_path=str(cover), config=cfg)
    assert first != second


def test_default_cover_bytes_participate_in_fingerprint(tmp_path: Path) -> None:
    default = tmp_path / "default.png"
    default.write_bytes(PNG)
    cfg = make_test_config(
        tmp_path,
        tmp_path / "default-fp.sqlite3",
        wechat_default_thumb_path=str(default),
    )
    first = draft_content_fingerprint(title="t", summary="s", body="b", cover_path="", config=cfg)
    Image = pytest.importorskip("PIL.Image")
    Image.new("RGB", (1, 1), (0, 255, 0)).save(default, format="PNG")
    second = draft_content_fingerprint(title="t", summary="s", body="b", cover_path="", config=cfg)
    assert first != second


def test_real_two_job_reuses_token_and_sanitized_thumb_with_exact_fingerprint(tmp_path: Path) -> None:
    cover = tmp_path / "articles" / "covers" / "cover.png"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(PNG)
    cfg = make_test_config(tmp_path, tmp_path / "real.sqlite3")
    calls = {"token": 0, "thumb": 0, "draft": 0}
    uploaded: list[bytes] = []

    def get_token(_url: str) -> dict:
        calls["token"] += 1
        return {"access_token": "token", "expires_in": 7200}

    def upload(_url: str, *, fields: dict, files: dict) -> dict:  # noqa: ARG001
        calls["thumb"] += 1
        uploaded.append(files["media"][1])
        return {"media_id": "thumb"}

    def create(_url: str, _payload: dict) -> dict:
        calls["draft"] += 1
        return {"media_id": f"draft-{calls['draft']}"}

    adapter = RealWechatAdapter(
        "app",
        "secret",
        managed_roots=(cfg.articles_dir,),
        project_root=cfg.root,
        http_get=get_token,
        http_post_multipart_fn=upload,
        http_post_json_fn=create,
    )
    first = adapter.create_draft(title="T", summary="S", body="B", cover_path=str(cover))
    second = adapter.create_draft(title="T2", summary="S2", body="B2", cover_path=str(cover))
    assert calls == {"token": 1, "thumb": 1, "draft": 2}
    assert len(uploaded) == 1
    assert first.raw_response["content_fingerprint"] == draft_content_fingerprint(
        title="T", summary="S", body="B", cover_path=str(cover), config=cfg
    )
    assert second.raw_response["content_fingerprint"] == draft_content_fingerprint(
        title="T2", summary="S2", body="B2", cover_path=str(cover), config=cfg
    )


def test_real_due_job_missing_credentials_stays_pending_before_adapter(tmp_path: Path, monkeypatch) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "preflight.sqlite3", wechat_mode="real")
    db.init_db(cfg.database_path)
    due = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds")
    with db.connect(cfg.database_path) as conn:
        article_id = conn.execute(
            "INSERT INTO articles (source_path,title,summary,body,content_hash,status) "
            "VALUES ('x.md','t','s','b','h','imported')"
        ).lastrowid
        conn.execute(
            "INSERT INTO publish_jobs (article_id,scheduled_at,status,adapter_mode) "
            "VALUES (?,?,'pending','real')",
            (article_id, due),
        )
        conn.commit()
    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda _cfg: (_ for _ in ()).throw(AssertionError("adapter constructed")),
    )
    result = run_due_jobs(cfg)
    assert result["skipped_preflight"] == 1
    with db.connect(cfg.database_path) as conn:
        assert conn.execute("SELECT status FROM publish_jobs").fetchone()[0] == "pending"
        assert conn.execute("SELECT COUNT(*) FROM scheduler_locks").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
