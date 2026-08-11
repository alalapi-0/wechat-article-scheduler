"""封面素材索引与草稿创建前检查。"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import struct
import zlib
from typing import Iterable
import warnings

from PIL import Image
from wechat_article_scheduler.filesystem_safety import (
    FileSnapshot,
    UnsafePathError,
    open_directory_handle,
    read_regular_file,
)


SUPPORTED_COVER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
MAX_COVER_BYTES = 10 * 1024 * 1024
_MAX_PNG_DIMENSION = 16_384
_MAX_PNG_PIXELS = 40_000_000
_MAX_PNG_DECODED_BYTES = 64 * 1024 * 1024
_MAX_PNG_CHUNKS = 4096
_MAX_PNG_IDAT_CHUNKS = 1024
_ADAM7_PASSES = (
    (0, 0, 8, 8),
    (4, 0, 8, 8),
    (0, 4, 4, 8),
    (2, 0, 4, 4),
    (0, 2, 2, 4),
    (1, 0, 2, 2),
    (0, 1, 1, 2),
)


@dataclass(frozen=True)
class CoverAsset:
    path: str
    name: str
    exists: bool
    size_bytes: int | None


class InvalidCoverError(ValueError):
    """A cover failed the local managed-image policy."""


def _png_scanline_sizes(
    width: int,
    height: int,
    bits_per_pixel: int,
    interlace: int,
) -> list[int] | None:
    if (
        width > _MAX_PNG_DIMENSION
        or height > _MAX_PNG_DIMENSION
        or width * height > _MAX_PNG_PIXELS
    ):
        return None
    passes = ((0, 0, 1, 1),) if interlace == 0 else _ADAM7_PASSES
    rows: list[int] = []
    total = 0
    for start_x, start_y, step_x, step_y in passes:
        if width <= start_x or height <= start_y:
            continue
        pass_width = (width - start_x + step_x - 1) // step_x
        pass_height = (height - start_y + step_y - 1) // step_y
        row_size = (pass_width * bits_per_pixel + 7) // 8
        total += pass_height * (row_size + 1)
        if total > _MAX_PNG_DECODED_BYTES:
            return None
        rows.extend([row_size] * pass_height)
    return rows


def _valid_png_zlib_stream(chunks: Iterable[memoryview], row_sizes: list[int]) -> bool:
    """Bound expansion to the exact PNG scanline budget and validate filters."""
    expected = sum(size + 1 for size in row_sizes)
    decoder = zlib.decompressobj()
    produced = 0
    row_index = 0
    row_offset = 0

    def consume(output: bytes) -> bool:
        nonlocal produced, row_index, row_offset
        produced += len(output)
        if produced > expected:
            return False
        offset = 0
        while offset < len(output):
            if row_index >= len(row_sizes):
                return False
            if row_offset == 0:
                if output[offset] > 4:
                    return False
                offset += 1
                row_offset = 1
                if offset == len(output):
                    continue
            remaining = row_sizes[row_index] - (row_offset - 1)
            consumed = min(remaining, len(output) - offset)
            offset += consumed
            row_offset += consumed
            if row_offset == row_sizes[row_index] + 1:
                row_index += 1
                row_offset = 0
        return True

    try:
        for chunk in chunks:
            pending = chunk
            while pending:
                remaining_budget = expected - produced
                output = decoder.decompress(pending, min(64 * 1024, remaining_budget + 1))
                pending = decoder.unconsumed_tail
                if decoder.unused_data or not consume(output):
                    return False
                if decoder.eof and pending:
                    return False
                if not output and pending:
                    return False
        output = decoder.flush(min(64 * 1024, expected - produced + 1))
        if not consume(output):
            return False
    except (ValueError, zlib.error):
        return False
    return (
        decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail
        and produced == expected
        and row_index == len(row_sizes)
        and row_offset == 0
    )


def _decoded_image_kind(data: bytes) -> str | None:
    """Validate image structure, not just a magic-byte prefix."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        view = memoryview(data)
        offset = 8
        seen_ihdr = False
        seen_iend = False
        seen_idat = False
        idat_ended = False
        chunk_count = 0
        idat_bytes = 0
        compressed_chunks: list[memoryview] = []
        width = height = bit_depth = color_type = interlace = 0
        while offset + 12 <= len(data):
            chunk_count += 1
            if chunk_count > _MAX_PNG_CHUNKS:
                return None
            length = struct.unpack_from(">I", view, offset)[0]
            if length > len(data) - offset - 12:
                return None
            kind = bytes(view[offset + 4 : offset + 8])
            payload = view[offset + 8 : offset + 8 + length]
            expected_crc = struct.unpack_from(">I", view, offset + 8 + length)[0]
            crc = zlib.crc32(kind)
            if zlib.crc32(payload, crc) & 0xFFFFFFFF != expected_crc:
                return None
            offset += 12 + length
            if kind == b"IHDR":
                if seen_ihdr or length != 13:
                    return None
                width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                    ">IIBBBBB", payload
                )
                if not width or not height or compression or filtering or interlace not in (0, 1):
                    return None
                seen_ihdr = True
            elif kind == b"IDAT":
                if not seen_ihdr or idat_ended or len(compressed_chunks) >= _MAX_PNG_IDAT_CHUNKS:
                    return None
                seen_idat = True
                idat_bytes += length
                if idat_bytes > MAX_COVER_BYTES:
                    return None
                compressed_chunks.append(payload)
            elif kind == b"IEND":
                seen_iend = length == 0
                break
            elif seen_idat:
                idat_ended = True
        if not (seen_ihdr and seen_iend and compressed_chunks) or offset != len(data):
            return None
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
        allowed_depths = {
            0: {1, 2, 4, 8, 16},
            2: {8, 16},
            3: {1, 2, 4, 8},
            4: {8, 16},
            6: {8, 16},
        }
        if channels is None or bit_depth not in allowed_depths[color_type]:
            return None
        row_sizes = _png_scanline_sizes(width, height, channels * bit_depth, interlace)
        if row_sizes is None or not _valid_png_zlib_stream(compressed_chunks, row_sizes):
            return None
        return "png"
    if data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"):
        pos = 2
        saw_frame = False
        saw_scan = False
        while pos < len(data) - 1:
            if data[pos] != 0xFF:
                if not saw_scan:
                    return None
                pos += 1
                continue
            while pos < len(data) and data[pos] == 0xFF:
                pos += 1
            if pos >= len(data):
                return None
            marker = data[pos]
            pos += 1
            if marker == 0xD9:
                break
            if marker == 0x00 or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(data):
                return None
            length = struct.unpack(">H", data[pos : pos + 2])[0]
            if length < 2 or pos + length > len(data):
                return None
            if marker in (0xC0, 0xC1, 0xC2):
                if length < 8:
                    return None
                height, width = struct.unpack(">HH", data[pos + 3 : pos + 7])
                if not width or not height:
                    return None
                saw_frame = True
            if marker == 0xDA:
                saw_scan = True
            pos += length
        return "jpeg" if saw_frame and saw_scan else None
    return None


def validate_image_bytes(data: bytes, suffix: str) -> str:
    if not data:
        raise InvalidCoverError("封面文件为空")
    if len(data) > MAX_COVER_BYTES:
        raise InvalidCoverError(f"封面文件不能超过 {MAX_COVER_BYTES // (1024 * 1024)} MB")
    ext = suffix.lower()
    if ext not in SUPPORTED_COVER_EXTENSIONS:
        raise InvalidCoverError("封面格式不支持；仅支持 JPG/JPEG/PNG")
    expected = "png" if ext == ".png" else "jpeg"
    if _decoded_image_kind(data) != expected:
        raise InvalidCoverError("封面内容损坏，或文件内容与扩展名不匹配")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if (image.format or "").lower() != expected:
                    raise InvalidCoverError("封面内容与扩展名不匹配")
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
                if image.width <= 0 or image.height <= 0:
                    raise InvalidCoverError("封面尺寸无效")
    except (InvalidCoverError, Image.DecompressionBombError):
        raise
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombWarning) as exc:
        raise InvalidCoverError("封面无法完整解码") from exc
    return expected


def secure_cover_bytes(path: Path, *, allowed_roots: Iterable[Path]) -> bytes:
    """Race-resistant read of a regular, unaliased image below an allowed root."""
    roots = tuple(allowed_roots)
    absolute = Path(os.path.abspath(path))
    try:
        snapshot = read_regular_file(
            absolute,
            allowed_roots=roots,
            max_bytes=MAX_COVER_BYTES,
        )
    except UnsafePathError as exc:
        raise InvalidCoverError(str(exc)) from exc
    return secure_cover_snapshot(snapshot, absolute.suffix)


def secure_cover_snapshot(snapshot: FileSnapshot, suffix: str) -> bytes:
    """Validate and sanitize bytes read from an already-authoritative file descriptor."""
    kind = validate_image_bytes(snapshot.data, suffix)
    try:
        with Image.open(BytesIO(snapshot.data)) as image:
            image.load()
            sanitized = BytesIO()
            if kind == "jpeg":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                image.save(sanitized, format="JPEG", quality=95)
            else:
                image.save(sanitized, format="PNG")
    except (OSError, ValueError) as exc:
        raise InvalidCoverError("封面无法安全重新编码") from exc
    payload = sanitized.getvalue()
    validate_image_bytes(payload, suffix)
    return payload


def index_cover_directory(root: Path) -> list[CoverAsset]:
    """索引 cover_assets 目录下的图片文件。"""
    try:
        directory = open_directory_handle(root, allowed_roots=(root,))
    except (OSError, UnsafePathError):
        return []
    assets: list[CoverAsset] = []
    try:
        with directory as handle:
            for name in handle.list_names():
                path = root / name
                if path.suffix.lower() not in SUPPORTED_COVER_EXTENSIONS:
                    continue
                try:
                    snapshot = handle.read_regular_file(name, max_bytes=MAX_COVER_BYTES)
                    data = secure_cover_snapshot(snapshot, path.suffix)
                except (UnsafePathError, InvalidCoverError):
                    continue
                assets.append(
                    CoverAsset(
                        path=str(path),
                        name=path.name,
                        exists=True,
                        size_bytes=len(data),
                    )
                )
    except (OSError, UnsafePathError):
        return assets
    return assets


def inspect_cover_path(path: str | Path | None) -> dict[str, object]:
    """校验单个封面文件；该函数不读取凭证且不触发网络。"""
    raw = str(path or "").strip()
    if not raw:
        return {"ok": False, "reason": "missing", "message": "未指定封面"}
    candidate = Path(raw)
    if candidate.suffix.lower() not in SUPPORTED_COVER_EXTENSIONS:
        return {
            "ok": False,
            "reason": "unsupported_type",
            "message": f"封面格式不支持：{candidate.name}；仅支持 JPG/JPEG/PNG",
        }
    try:
        size = len(secure_cover_bytes(candidate, allowed_roots=(candidate.parent,)))
    except InvalidCoverError as exc:
        return {
            "ok": False,
            "reason": "invalid_image",
            "message": str(exc),
        }
    return {
        "ok": True,
        "reason": "ok",
        "resolved_path": str(candidate),
        "size_bytes": size,
        "message": "封面可用",
    }


def managed_cover_roots(config: object) -> tuple[Path, ...]:
    return (
        Path(getattr(config, "covers_dir")),
        Path(getattr(config, "root")) / "cover_assets",
        Path(getattr(config, "root")) / "assets" / "covers",
    )


def managed_cover_bytes(config: object, path: str | Path) -> bytes:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(getattr(config, "root")) / candidate
    return secure_cover_bytes(candidate, allowed_roots=managed_cover_roots(config))


def inspect_managed_cover(config: object, path: str | Path | None) -> dict[str, object]:
    raw = str(path or "").strip()
    if not raw:
        return {"ok": False, "reason": "missing", "message": "未指定封面"}
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path(getattr(config, "root")) / candidate
    try:
        data = managed_cover_bytes(config, candidate)
    except InvalidCoverError as exc:
        return {"ok": False, "reason": "invalid_managed_cover", "message": str(exc)}
    return {
        "ok": True,
        "reason": "ok",
        "resolved_path": str(Path(os.path.abspath(candidate))),
        "size_bytes": len(data),
        "message": "封面可用",
    }


def check_configured_cover(
    config: object, path: str | Path | None
) -> dict[str, object]:
    """Article covers must be managed; only the exact configured default may be external."""
    raw = str(path or "").strip()
    if raw:
        return {**inspect_managed_cover(config, raw), "using_default": False}
    default_raw = str(getattr(config, "wechat_default_thumb_path", "") or "").strip()
    if not default_raw:
        return {"ok": False, "reason": "missing", "using_default": False, "message": "缺少封面且未配置默认封面"}
    result = inspect_cover_path(default_raw)
    return {**result, "using_default": True}


def check_cover_path(
    path: str | Path | None,
    *,
    default_thumb: str | Path | None = None,
) -> dict[str, object]:
    """解析文章封面或默认封面，并返回统一的本地校验结果。"""
    raw = str(path or "").strip()
    if raw:
        result = inspect_cover_path(raw)
        return {**result, "using_default": False}

    default_raw = str(default_thumb or "").strip()
    if default_raw:
        result = inspect_cover_path(default_raw)
        if result["ok"]:
            return {
                **result,
                "using_default": True,
                "message": "未指定文章封面，将使用默认封面",
            }
        return {
            **result,
            "using_default": True,
            "message": f"默认封面不可用：{result['message']}",
        }
    return {
        "ok": False,
        "reason": "missing",
        "using_default": False,
        "message": "缺少封面且未配置默认封面",
    }
