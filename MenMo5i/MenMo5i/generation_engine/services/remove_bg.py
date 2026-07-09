"""
Background-removal pipeline for logo images.

Processing always happens **in-memory** — no intermediate files touch disk.

Dependencies
------------
    pip install rembg Pillow

The first call to ``rembg`` will download the U²-Net model (~170 MB) and
cache it under ``~/.u2net/``.
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageFilter
from rembg import remove as rembg_remove

logger = logging.getLogger(__name__)


# ── Mandatory rembg pipeline (bytes in / bytes out) ─────────────────────


def remove_background_bytes(image_data: bytes) -> bytes:
    """
    Strip the background from raw image bytes using ``rembg.remove()``.

    All processing is performed strictly in-memory via ``io.BytesIO``;
    **no intermediate file is ever written to disk**.

    Parameters
    ----------
    image_data : bytes
        The raw binary payload of the source image (any format Pillow can
        open, e.g. PNG / JPEG / WebP).

    Returns
    -------
    bytes
        A clean transparent PNG as raw bytes, ready to be wrapped in a
        Django ``ContentFile`` and saved to an ``ImageField``.

    Raises
    ------
    RuntimeError
        If rembg processing fails for any reason.
    """
    try:
        input_stream = io.BytesIO(image_data)
        output_stream = io.BytesIO()

        input_stream.seek(0)
        result_bytes = rembg_remove(input_stream.read())

        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        result.save(output_stream, format="PNG")

        return output_stream.getvalue()

    except Exception as exc:
        logger.exception("rembg removal failed")
        raise RuntimeError(f"Background removal failed: {exc}") from exc


# ── Legacy PIL‑based wrappers (kept for backward compatibility) ─────────


def remove_background(img: Image.Image) -> Image.Image:
    """
    Legacy wrapper — accepts a PIL ``Image`` and returns a PIL ``Image``
    with a transparent background.

    Internally round-trips through :func:`remove_background_bytes` for
    consistent results.
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    cleaned = remove_background_bytes(buf.getvalue())
    return Image.open(io.BytesIO(cleaned)).convert("RGBA")


def add_shadow(design: Image.Image, offset=(8, 12), blur_radius=12, opacity=0.35) -> Image.Image:
    """
    Add a realistic drop shadow to a transparent design.
    """
    alpha = design.split()[3]
    w, h = design.size

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            a = alpha.getpixel((x, y))
            if a > 0:
                shadow.putpixel((x, y), (0, 0, 0, int(a * opacity)))

    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    result.paste(shadow, offset)
    result = Image.alpha_composite(result, design)
    return result
