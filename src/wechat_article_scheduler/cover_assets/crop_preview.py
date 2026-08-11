"""封面裁剪与双比例预览。"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from wechat_article_scheduler.cover_assets.index import InvalidCoverError, secure_cover_bytes

ASPECT_HORIZONTAL = 2.35
ASPECT_SQUARE = 1.0
HORIZONTAL_LABEL = "2.35:1"
SQUARE_LABEL = "1:1"


def pillow_available() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except ImportError:
        return False


def parse_cover_config(raw: str | dict | None) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    data = json.loads(raw) if isinstance(raw, str) else raw
    return data if isinstance(data, dict) else {}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_crop_dict(crop: dict[str, Any]) -> dict[str, float]:
    x = _clamp01(crop.get("x", 0))
    y = _clamp01(crop.get("y", 0))
    w = _clamp01(crop.get("width", 1))
    h = _clamp01(crop.get("height", 1))
    if w <= 0:
        w = 0.01
    if h <= 0:
        h = 0.01
    if x + w > 1:
        w = 1 - x
    if y + h > 1:
        h = 1 - y
    return {"x": x, "y": y, "width": w, "height": h}


def crop_focal_point(crop: dict[str, Any]) -> dict[str, float]:
    c = normalize_crop_dict(crop)
    return {
        "x": _clamp01(c["x"] + c["width"] / 2),
        "y": _clamp01(c["y"] + c["height"] / 2),
    }


def enrich_cover_config(raw: str | dict | None) -> dict[str, Any]:
    """确保配置含 crop 与 focal（由 crop 中心推导）。"""
    data = parse_cover_config(raw)
    crop = data.get("crop")
    if isinstance(crop, dict):
        data["crop"] = normalize_crop_dict(crop)
        data["focal"] = crop_focal_point(data["crop"])
    return data


def _norm_to_pixels(
    crop: dict[str, float], iw: int, ih: int
) -> tuple[float, float, float, float]:
    return (
        crop["x"] * iw,
        crop["y"] * ih,
        crop["width"] * iw,
        crop["height"] * ih,
    )


def square_crop_from_focal(
    iw: int, ih: int, focal: dict[str, float]
) -> dict[str, float]:
    """以 focal 为中心的最大内接正方形（像素级再归一化）。"""
    fx = focal["x"] * iw
    fy = focal["y"] * ih
    half = min(fx, fy, iw - fx, ih - fy)
    if half <= 0:
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    side = half * 2
    x0 = fx - half
    y0 = fy - half
    return {
        "x": _clamp01(x0 / iw),
        "y": _clamp01(y0 / ih),
        "width": _clamp01(side / iw),
        "height": _clamp01(side / ih),
    }


def crop_for_aspect(
    iw: int,
    ih: int,
    *,
    crop: dict[str, Any] | None,
    aspect: float,
) -> dict[str, float]:
    """返回指定比例的归一化裁剪区域。"""
    if not crop:
        if aspect >= ASPECT_SQUARE + 0.1:
            # 横向默认：居中裁 2.35:1
            target_h_ratio = iw / (ih * aspect) if ih else 1.0
            if target_h_ratio >= 1:
                return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
            y0 = (1 - target_h_ratio) / 2
            return {"x": 0.0, "y": y0, "width": 1.0, "height": target_h_ratio}
        side = min(iw, ih)
        x0 = (iw - side) / 2 / iw
        y0 = (ih - side) / 2 / ih
        s = side / iw
        sh = side / ih
        return {"x": x0, "y": y0, "width": s, "height": sh}

    base = normalize_crop_dict(crop)
    if abs(aspect - ASPECT_HORIZONTAL) < 0.05:
        return base
    focal = crop_focal_point(base)
    return square_crop_from_focal(iw, ih, focal)


def _cover_bytes(path: Path, allowed_roots: tuple[Path, ...]) -> bytes:
    return secure_cover_bytes(path, allowed_roots=allowed_roots)


def probe_image_size(
    path: Path, *, allowed_roots: tuple[Path, ...]
) -> tuple[int, int] | None:
    """Read verified image dimensions from no-follow in-memory bytes."""
    from PIL import Image

    try:
        data = _cover_bytes(path, allowed_roots)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            return image.size
    except (InvalidCoverError, OSError, ValueError):
        return None


def css_background_spec(crop: dict[str, float]) -> dict[str, str]:
    """供 Web/CSS 近似预览的定位参数（百分比）。"""
    c = normalize_crop_dict(crop)
    px = 100 / c["width"]
    py = 100 / c["height"]
    pos_x = -c["x"] * px
    pos_y = -c["y"] * py
    return {
        "background_size": f"{px:.4f}% {py:.4f}%",
        "background_position": f"{pos_x:.4f}% {pos_y:.4f}%",
    }


def _render_jpeg_bytes(data: bytes, crop: dict[str, float], *, max_edge: int = 640) -> bytes | None:
    if not pillow_available():
        return None
    from PIL import Image

    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        iw, ih = im.size
        x0, y0, w, h = _norm_to_pixels(normalize_crop_dict(crop), iw, ih)
        box = (int(x0), int(y0), int(x0 + w), int(y0 + h))
        cropped = im.crop(box)
        if max(cropped.size) > max_edge:
            cropped.thumbnail((max_edge, max_edge))
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def build_preview_variant(
    path: Path,
    *,
    crop: dict[str, float],
    aspect_label: str,
    aspect_value: float,
    image_bytes: bytes | None = None,
    allowed_roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    data = image_bytes
    if data is None:
        try:
            if allowed_roots is None:
                raise InvalidCoverError("预览缺少明确的受管目录")
            data = _cover_bytes(path, allowed_roots)
        except InvalidCoverError:
            data = None
    size = probe_image_size(path) if data is None else _image_size_from_bytes(data)
    iw, ih = size if size else (1, 1)
    css = css_background_spec(crop)
    variant: dict[str, Any] = {
        "aspect": aspect_label,
        "aspect_value": aspect_value,
        "crop": crop,
        "css": css,
        "image_width": iw,
        "image_height": ih,
    }
    jpeg = _render_jpeg_bytes(data, crop) if data is not None else None
    if jpeg:
        variant["render_mode"] = "jpeg"
        variant["image_base64"] = base64.b64encode(jpeg).decode("ascii")
    else:
        variant["render_mode"] = "css"
        variant["image_base64"] = None
    return variant


def build_dual_cover_previews(
    cover_path: str | Path,
    cover_config_json: str | dict | None = None,
    *,
    allowed_roots: tuple[Path, ...],
) -> dict[str, Any]:
    """生成横向（2.35:1）与方形（1:1）预览规格/可选 JPEG。"""
    path = Path(cover_path)
    cfg = enrich_cover_config(cover_config_json)
    crop = cfg.get("crop") if isinstance(cfg.get("crop"), dict) else None
    try:
        image_bytes = _cover_bytes(path, allowed_roots)
    except InvalidCoverError:
        image_bytes = None
    size = _image_size_from_bytes(image_bytes) if image_bytes is not None else None
    if size is None:
        return {
            "ok": False,
            "message": "封面文件不存在或无法读取尺寸",
            "pillow_available": pillow_available(),
        }
    iw, ih = size
    h_crop = crop_for_aspect(iw, ih, crop=crop, aspect=ASPECT_HORIZONTAL)
    s_crop = crop_for_aspect(iw, ih, crop=crop, aspect=ASPECT_SQUARE)
    return {
        "ok": True,
        "pillow_available": pillow_available(),
        "cover_path": str(path),
        "config": cfg,
        "horizontal": build_preview_variant(
            path,
            crop=h_crop,
            aspect_label=HORIZONTAL_LABEL,
            aspect_value=ASPECT_HORIZONTAL,
            image_bytes=image_bytes,
        ),
        "square": build_preview_variant(
            path,
            crop=s_crop,
            aspect_label=SQUARE_LABEL,
            aspect_value=ASPECT_SQUARE,
            image_bytes=image_bytes,
        ),
    }


def _image_size_from_bytes(data: bytes) -> tuple[int, int] | None:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            return image.size
    except (OSError, ValueError):
        return None
