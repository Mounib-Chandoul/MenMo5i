import io
import logging
import os
import random

import replicate
from django.conf import settings
from PIL import Image

from .gemini_inference import generate_image as gemini_generate
from .pollinations_inference import generate_image as pollinations_generate
from .prompt_engine import enhance_prompt

logger = logging.getLogger(__name__)

TARGET_SIZE = (2048, 2048)


def _upscale(img: Image.Image) -> Image.Image:
    """Upscale image to TARGET_SIZE using high-quality LANCZOS resampling."""
    if img.size == TARGET_SIZE:
        return img
    return img.resize(TARGET_SIZE, Image.LANCZOS)


def _get_client():
    token = getattr(settings, 'REPLICATE_API_TOKEN', '') or os.getenv('REPLICATE_API_TOKEN', '')
    if token:
        os.environ.setdefault('REPLICATE_API_TOKEN', token)
    return replicate


def _generate_fallback_design(prompt: str, has_background: bool = False) -> Image.Image:
    """
    Last-resort procedural design when all AI backends are unavailable.

    Instead of drawing random geometric shapes that have nothing to do with
    the prompt, this renders a bold text-banner t-shirt design using the
    prompt text itself as the primary visual element.
    """
    from PIL import ImageDraw, ImageFont

    W, H = 1024, 1024
    bg_color = (255, 255, 255, 255) if has_background else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (W, H), bg_color)
    draw = ImageDraw.Draw(canvas)

    prompt_lower = prompt.lower()
    rng = random.Random(hash(prompt) & 0xFFFFFFFF)

    # Pick a colour palette from the prompt
    palettes = {
        "violet": [(130, 80, 245), (100, 50, 230)],
        "purple": [(150, 50, 235), (170, 85, 250)],
        "cyan":   [(0, 185, 215), (35, 215, 240)],
        "green":  [(35, 200, 95), (75, 225, 130)],
        "red":    [(240, 70, 70), (250, 115, 115)],
        "blue":   [(60, 130, 250), (100, 170, 255)],
        "orange": [(255, 150, 60), (255, 195, 40)],
        "neon":   [(255, 0, 255), (0, 255, 255)],
    }
    color_key = "violet"
    for k in palettes:
        if k in prompt_lower:
            color_key = k
            break
    primary = palettes[color_key][0] + (255,)
    accent = palettes[color_key][1] + (255,)
    white = (255, 255, 255, 255)

    cx, cy = W // 2, H // 2

    # Background accent shape
    for i in range(3):
        r = 400 - i * 120
        draw.rounded_rectangle(
            [cx - r, cy - r, cx + r, cy + r],
            radius=60, fill=(*palettes[color_key][0], 30 + i * 20),
        )

    # Extract a short label from the prompt
    label = prompt.strip().strip(",").strip()
    # Truncate to first ~20 chars for the display
    if len(label) > 24:
        label = label[:24] + "…"

    # Try to load a bold font, fall back to default
    font_size = 100
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Measure text using getbbox
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Shrink font until it fits
    while tw > W - 120 and font_size > 20:
        font_size -= 10
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", font_size)
            except (OSError, IOError):
                pass
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Draw main text with shadow
    tx = (W - tw) // 2
    ty = (H - th) // 2 - 60
    draw.text((tx + 4, ty + 4), label, fill=(0, 0, 0, 180), font=font)
    draw.text((tx, ty), label, fill=primary, font=font)

    # Decorative underline
    underline_y = ty + th + 20
    draw.rounded_rectangle(
        [cx - tw // 2 - 20, underline_y, cx + tw // 2 + 20, underline_y + 8],
        radius=4, fill=accent,
    )

    # Sub-label with category/quality tag
    tag = "T-SHIRT DESIGN"
    try:
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except (OSError, IOError):
        small_font = ImageFont.load_default()
    bbox2 = draw.textbbox((0, 0), tag, font=small_font)
    stw = bbox2[2] - bbox2[0]
    draw.text(((W - stw) // 2, underline_y + 30), tag, fill=accent, font=small_font)

    return canvas


def _run_replicate(model: str, inputs: dict) -> Image.Image:
    output = _get_client().run(model, input=inputs)
    image_url = output[0] if isinstance(output, list) else output
    import urllib.request
    resp = urllib.request.urlopen(image_url, timeout=60)
    return Image.open(io.BytesIO(resp.read())).convert("RGBA")


def generate_design_from_prompt(
    prompt: str,
    category: str = "",
    style: str = "",
    has_background: bool = False,
) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt.

    Provider chain (each fallback activates on exception):
    1. Gemini 2.0 Flash         (free, modern — requires API key)
    2. Pollinations.ai          (free, no token)
    3. Procedural PIL fallback  (always works — text-based, no rings)

    When ``has_background=False`` (default) the result has a transparent
    background suitable for compositing onto a shirt.
    """
    enhanced = enhance_prompt(prompt, category=category, style=style)
    logger.info("Enhanced prompt: %s", enhanced)

    def _remove_bg(img: Image.Image) -> Image.Image:
        if has_background:
            return img
        from .remove_bg import remove_background
        return remove_background(img)

    # 1 — Gemini 2.0 Flash (primary)
    try:
        raw_bytes = gemini_generate(enhanced)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        img = _upscale(img)
        return _remove_bg(img)
    except Exception as exc:
        logger.warning("Gemini failed for prompt=%r: %s", prompt, exc)

    # 2 — Pollinations (free, no API key needed)
    try:
        raw_bytes = pollinations_generate(enhanced)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        return _remove_bg(img)
    except Exception as exc:
        logger.warning("Pollinations fallback failed for prompt=%r: %s", prompt, exc)

    # 3 — Procedural PIL fallback (text banner)
    return _generate_fallback_design(enhanced, has_background=has_background)


def generate_design_from_prompt_and_image(prompt: str, inspiration_path: str) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt + inspiration image.
    Uses Gemini 2.0 Flash multimodal (image + text input).
    """
    try:
        enhanced = enhance_prompt(prompt)
        raw_bytes = gemini_generate(enhanced, image_path=inspiration_path)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception as exc:
        logger.warning("Gemini img2img failed for prompt=%r: %s", prompt, exc)
    return generate_design_from_prompt(prompt)


def render_mockup_scene(composited_image_url: str, mask_image_url: str, user_prompt: str) -> str:
    output = _get_client().run(
        "lucataco/sdxl-inpainting:a5b13068cc81a89a4fbeefeccc774869fcb34df4dbc92c1555e0f2771d49dde7",
        input={
            "image": composited_image_url,
            "mask": mask_image_url,
            "prompt": f"A high-end streetwear lookbook style photo of a person wearing this t-shirt, {user_prompt}, 4k, cinematic studio lighting, highly detailed structure",
            "negative_prompt": "blurry, low quality, warped artwork, distorted graphic text, low resolution, deformed face, bad anatomy",
            "num_inference_steps": 30,
            "guidance_scale": 8.0,
        },
    )
    return output[0]
