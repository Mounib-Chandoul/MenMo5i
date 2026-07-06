import io
import logging
import math
import os
import random

import replicate
from django.conf import settings
from PIL import Image, ImageDraw

from .hf_inference import generate_image_from_prompt as hf_generate
from .prompt_engine import enhance_prompt, NEGATIVE_PROMPT

logger = logging.getLogger(__name__)


def _get_client():
    token = getattr(settings, 'REPLICATE_API_TOKEN', '') or os.getenv('REPLICATE_API_TOKEN', '')
    if token:
        os.environ.setdefault('REPLICATE_API_TOKEN', token)
    return replicate


def _generate_fallback_design(prompt: str) -> Image.Image:
    """Generate a vibrant, fully-opaque geometric T-shirt design."""
    W, H = 1024, 1024
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    prompt_lower = prompt.lower()
    rng = random.Random(hash(prompt) & 0xFFFFFFFF)

    palettes = {
        "violet": [(130, 80, 245), (100, 50, 230), (170, 140, 250), (200, 180, 255)],
        "purple": [(150, 50, 235), (170, 85, 250), (195, 135, 255), (220, 185, 255)],
        "cyan":   [(0, 185, 215), (35, 215, 240), (105, 235, 250), (170, 245, 255)],
        "green":  [(35, 200, 95), (75, 225, 130), (140, 245, 175), (190, 250, 210)],
        "red":    [(240, 70, 70), (250, 115, 115), (255, 170, 170), (255, 205, 205)],
        "blue":   [(60, 130, 250), (100, 170, 255), (150, 200, 255), (195, 220, 255)],
        "orange": [(255, 150, 60), (255, 195, 40), (255, 235, 140), (255, 245, 200)],
        "neon":   [(255, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 128)],
    }

    color_key = "violet"
    for k in palettes:
        if k in prompt_lower:
            color_key = k
            break
    colors = palettes[color_key]
    # Fully opaque
    colors = [c + (255,) for c in colors]

    cx, cy = W // 2, H // 2

    if "skull" in prompt_lower or "death" in prompt_lower or "dark" in prompt_lower:
        # Bold skull-like abstract
        r = 240
        draw.ellipse([cx - r, cy - r - 80, cx + r, cy + r - 80], fill=colors[0])
        draw.ellipse([cx - 100, cy - 120, cx - 40, cy - 30], fill=colors[1])
        draw.ellipse([cx + 40, cy - 120, cx + 100, cy - 30], fill=colors[1])
        draw.arc([cx - 130, cy + 30, cx + 130, cy + 160], 0, 180, fill=colors[2], width=18)
        for i in range(-4, 5):
            tx = cx + i * 28
            draw.rectangle([tx - 10, cy + 90, tx + 10, cy + 130], fill=colors[3])

    elif "flower" in prompt_lower or "nature" in prompt_lower or "plant" in prompt_lower or "rose" in prompt_lower or "lotus" in prompt_lower:
        # Layered flower
        for i in range(8):
            angle = i * math.pi / 4
            px = cx + int(140 * math.cos(angle))
            py = cy + int(140 * math.sin(angle))
            draw.ellipse([px - 70, py - 70, px + 70, py + 70], fill=colors[i % len(colors)])
        draw.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=colors[0])

    elif "geometric" in prompt_lower or "pattern" in prompt_lower or "mandala" in prompt_lower:
        # Rich geometric mandala
        for ring in range(6):
            r = 60 + ring * 70
            n = 8 + ring * 4
            for i in range(n):
                angle = i * (2 * math.pi / n) + ring * 0.2
                px = cx + int(r * math.cos(angle))
                py = cy + int(r * math.sin(angle))
                size = 60 - ring * 6
                draw.ellipse([px - size, py - size, px + size, py + size],
                             fill=colors[ring % len(colors)])
        draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=colors[0])

    elif "abstract" in prompt_lower:
        # Bold overlapping circles
        for i in range(6):
            angle = i * math.pi / 3
            offset = 90
            px = cx + int(offset * math.cos(angle))
            py = cy + int(offset * math.sin(angle))
            r = 160 - i * 15
            draw.ellipse([px - r, py - r, px + r, py + r], fill=colors[i % len(colors)])

    elif "tribal" in prompt_lower or "cyberpunk" in prompt_lower or "neon" in prompt_lower:
        # Bold angular tribal
        points = []
        for i in range(12):
            angle = i * math.pi / 6
            r = 300 if i % 2 == 0 else 150
            points.append((cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle))))
        draw.polygon(points, fill=colors[0])
        for i in range(8):
            angle = i * math.pi / 4
            px = cx + int(200 * math.cos(angle))
            py = cy + int(200 * math.sin(angle))
            draw.ellipse([px - 50, py - 50, px + 50, py + 50], fill=colors[1])

    elif "star" in prompt_lower or "sun" in prompt_lower or "moon" in prompt_lower or "space" in prompt_lower:
        # Star/sun burst
        outer_r = 350
        inner_r = 120
        n_points = 24
        star = []
        for i in range(n_points * 2):
            angle = i * math.pi / n_points - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            star.append((cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle))))
        draw.polygon(star, fill=colors[0])
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], fill=colors[3])

    elif "wave" in prompt_lower or "ocean" in prompt_lower or "water" in prompt_lower:
        # Layered waves
        for row in range(5):
            y_base = 150 + row * 170
            for col in range(-1, 4):
                wx = col * 350 + (row % 2) * 175
                wy = y_base
                for phase in range(3):
                    x_off = int(40 * math.sin(row + phase * 1.5))
                    y_off = int(20 * math.cos(col + phase))
                    draw.ellipse([wx + x_off - 120, wy + y_off - 60, wx + x_off + 120, wy + y_off + 60],
                                 fill=colors[(row + phase) % len(colors)])

    else:
        # Bold concentric rings with centerpiece
        for i in range(8):
            r = 350 - i * 40
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=colors[i % len(colors)])
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], fill=colors[0])
        for i in range(8):
            angle = i * math.pi / 4
            px = cx + int(200 * math.cos(angle))
            py = cy + int(200 * math.sin(angle))
            draw.line([(cx, cy), (px, py)], fill=colors[1], width=12)
        for i in range(8):
            angle = i * math.pi / 4 + math.pi / 8
            px = cx + int(130 * math.cos(angle))
            py = cy + int(130 * math.sin(angle))
            draw.ellipse([px - 20, py - 20, px + 20, py + 20], fill=colors[3])

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
) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt.

    Provider chain (each fallback activates on exception):
    1. Replicate Flux Schnell  (fast, high quality)
    2. Hugging Face SDXL        (serverless, no GPU needed locally)
    3. Procedural PIL fallback  (always works, vibrant output)

    The raw *user* prompt is first passed through the prompt-engine so every
    provider receives an enriched description.
    """
    enhanced = enhance_prompt(prompt, category=category, style=style)
    logger.info("Enhanced prompt: %s", enhanced)

    try:
        img = _run_replicate("black-forest-labs/flux-schnell", {
            "prompt": enhanced + ", clean white background",
            "num_outputs": 1,
            "num_inference_steps": 4,
            "output_format": "png",
        })
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception as exc:
        logger.warning("Replicate failed for prompt=%r: %s", prompt, exc)

    try:
        raw_bytes = hf_generate(
            prompt=enhanced,
            negative_prompt=NEGATIVE_PROMPT,
        )
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception as exc:
        logger.warning("Hugging Face fallback also failed for prompt=%r: %s", prompt, exc)

    return _generate_fallback_design(enhanced)


def generate_design_from_prompt_and_image(prompt: str, inspiration_path: str) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt + inspiration image.
    Uses Replicate SDXL img2img.
    """
    try:
        enhanced = enhance_prompt(prompt)
        img = _run_replicate(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            {
                "width": 1024,
                "height": 1024,
                "image": inspiration_path,
                "prompt": enhanced + ", clean white background",
                "negative_prompt": NEGATIVE_PROMPT,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "strength": 0.7,
            },
        )
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception:
        pass
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
