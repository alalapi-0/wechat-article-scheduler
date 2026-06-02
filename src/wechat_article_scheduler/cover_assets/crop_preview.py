"""封面裁剪与双比例预览（Round 62 / 收敛 Phase 1 Round 7）。"""

from __future__ import annotations

import base64
import io
import json
import struct
from pathlib import Path
from typing import Any

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


def probe_image_size(path: Path) -> tuple[int, int] | None:
    """读取图片尺寸；优先 Pillow，否则解析 PNG/JPEG 头。"""
    if not path.is_file():
        return None
    if pillow_available():
        from PIL import Image

        with Image.open(path) as im:
            return im.size
    data = path.read_bytes()[:64]
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    if len(data) >= 2 and data[0:2] == b"\xff\xd8":
        return _jpeg_size(path)
    return None


def _jpeg_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as f:
        f.read(2)
        while True:
            marker = f.read(2)
            if len(marker) < 2:
                return None
            if marker[0] != 0xFF:
                return None
            while marker[0] == 0xFF and marker[1] == 0xFF:
                marker = f.read(1) + f.read(1)
            kind = marker[1]
            if kind in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                length = struct.unpack(">H", f.read(2))[0]
                data = f.read(length - 2)
                h, w = struct.unpack(">HH", data[1:5])
                return int(w), int(h)
            if kind in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD8, 0xD9):
                continue
            length = struct.unpack(">H", f.read(2))[0]
            f.read(length - 2)


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


def _render_jpeg_bytes(path: Path, crop: dict[str, float], *, max_edge: int = 640) -> bytes | None:
    if not pillow_available():
        return None
    from PIL import Image

    with Image.open(path) as im:
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
) -> dict[str, Any]:
    size = probe_image_size(path)
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
    jpeg = _render_jpeg_bytes(path, crop)
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
) -> dict[str, Any]:
    """生成横向（2.35:1）与方形（1:1）预览规格/可选 JPEG。"""
    path = Path(cover_path)
    cfg = enrich_cover_config(cover_config_json)
    crop = cfg.get("crop") if isinstance(cfg.get("crop"), dict) else None
    size = probe_image_size(path)
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
        ),
        "square": build_preview_variant(
            path,
            crop=s_crop,
            aspect_label=SQUARE_LABEL,
            aspect_value=ASPECT_SQUARE,
        ),
    }
