import io
import math
import os
import random

import replicate
from django.conf import settings
from PIL import Image, ImageDraw


def _get_client():
    token = getattr(settings, 'REPLICATE_API_TOKEN', '') or os.getenv('REPLICATE_API_TOKEN', '')
    if token:
        os.environ.setdefault('REPLICATE_API_TOKEN', token)
    return replicate


def _generate_fallback_design(prompt: str) -> Image.Image:
    """Generate a simple geometric T-shirt design from prompt keywords."""
    W, H = 1024, 1024
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    prompt_lower = prompt.lower()
    rng = random.Random(hash(prompt) & 0xFFFFFFFF)

    # Pick a color scheme based on prompt keywords
    palettes = {
        "violet": [(139, 92, 246), (124, 58, 237), (167, 139, 250), (196, 181, 253)],
        "purple": [(147, 51, 234), (168, 85, 247), (192, 132, 252), (216, 180, 254)],
        "cyan": [(6, 182, 212), (34, 211, 238), (103, 232, 249), (165, 243, 252)],
        "green": [(34, 197, 94), (74, 222, 128), (134, 239, 172), (187, 247, 208)],
        "red": [(239, 68, 68), (248, 113, 113), (252, 165, 165), (254, 202, 202)],
        "blue": [(59, 130, 246), (96, 165, 250), (147, 197, 253), (191, 219, 254)],
        "orange": [(251, 146, 60), (251, 191, 36), (253, 230, 138), (254, 243, 199)],
        "neon": [(255, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 128)],
    }

    color_key = "violet"
    for k in palettes:
        if k in prompt_lower:
            color_key = k
            break
    colors = palettes[color_key]

    if "skull" in prompt_lower or "death" in prompt_lower or "dark" in prompt_lower:
        # Skull-like abstract shape
        cx, cy = W // 2, H // 2
        r = 200
        draw.ellipse([cx - r, cy - r - 60, cx + r, cy + r - 60], fill=colors[0] + (200,))
        draw.ellipse([cx - 80, cy - 100, cx - 30, cy - 20], fill=colors[1] + (220,))
        draw.ellipse([cx + 30, cy - 100, cx + 80, cy - 20], fill=colors[1] + (220,))
        # Mouth
        draw.arc([cx - 100, cy + 40, cx + 100, cy + 140], 0, 180, fill=colors[2] + (200,), width=12)
        # Teeth
        for i in range(-3, 4):
            tx = cx + i * 25
            draw.rectangle([tx - 8, cy + 100, tx + 8, cy + 130], fill=colors[3] + (180,))
    elif "flower" in prompt_lower or "nature" in prompt_lower or "plant" in prompt_lower:
        # Geometric flower
        cx, cy = W // 2, H // 2
        for i in range(8):
            angle = i * math.pi / 4
            px = cx + int(120 * math.cos(angle))
            py = cy + int(120 * math.sin(angle))
            draw.ellipse([px - 60, py - 60, px + 60, py + 60], fill=colors[i % len(colors)] + (180,))
        draw.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], fill=colors[0] + (220,))
    elif "geometric" in prompt_lower or "abstract" in prompt_lower or "pattern" in prompt_lower:
        # Abstract geometric pattern
        for _ in range(30):
            x = rng.randint(0, W)
            y = rng.randint(0, H)
            s = rng.randint(30, 150)
            rot = rng.randint(0, 360)
            c = rng.choice(colors) + (rng.randint(120, 220),)
            shape_type = rng.choice(["circle", "rect", "triangle"])
            if shape_type == "circle":
                draw.ellipse([x - s // 2, y - s // 2, x + s // 2, y + s // 2], fill=c)
            elif shape_type == "rect":
                r_rect = [
                    x - s // 2,
                    y - s // 2,
                    x + s // 2,
                    y + s // 2,
                ]
                draw.rectangle(r_rect, fill=c)
            else:
                draw.polygon([
                    (x, y - s // 2),
                    (x - s // 2, y + s // 2),
                    (x + s // 2, y + s // 2),
                ], fill=c)
    else:
        # Default: concentric shapes with the brand aesthetic
        cx, cy = W // 2, H // 2
        for i in range(10):
            r = 220 - i * 20
            alpha = 200 - i * 15
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=colors[i % len(colors)] + (max(alpha, 40),), width=8)
        # Central mark
        draw.ellipse([cx - 60, cy - 60, cx + 60, cy + 60],
                     fill=colors[0] + (200,))
        # Star-like rays
        for i in range(12):
            angle = i * math.pi / 6
            px = cx + int(160 * math.cos(angle))
            py = cy + int(160 * math.sin(angle))
            draw.line([(cx, cy), (px, py)], fill=colors[1] + (160,), width=6)

    return canvas


def _run_replicate(model: str, inputs: dict) -> Image.Image:
    """Run a Replicate model and return the result as an RGBA PIL Image."""
    output = _get_client().run(model, input=inputs)
    image_url = output[0] if isinstance(output, list) else output
    import urllib.request
    resp = urllib.request.urlopen(image_url, timeout=60)
    return Image.open(io.BytesIO(resp.read())).convert("RGBA")


def generate_design_from_prompt(prompt: str) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt.
    Tries Replicate Flux Schnell first; falls back to procedural PIL design.

    Returns RGBA PIL Image with transparent background.
    """
    try:
        img = _run_replicate("black-forest-labs/flux-schnell", {
            "prompt": f"t-shirt print design, {prompt}, flat vector illustration, high contrast, graphic design, bold lines, clean, white background",
            "num_outputs": 1,
            "num_inference_steps": 4,
            "output_format": "png",
        })
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception:
        pass

    return _generate_fallback_design(prompt)


def generate_design_from_prompt_and_image(prompt: str, inspiration_path: str) -> Image.Image:
    """
    Generate a t-shirt print design from a text prompt + inspiration image.
    Uses Replicate SDXL img2img to blend the prompt with the reference image.

    Returns RGBA PIL Image with transparent background.
    """
    try:
        import urllib.request
        img = _run_replicate(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            {
                "width": 1024,
                "height": 1024,
                "image": inspiration_path,
                "prompt": f"t-shirt print design, {prompt}, flat vector illustration, high contrast, graphic design, bold lines, clean, white background",
                "negative_prompt": "photo, realistic, 3d, low quality, blurry, distorted",
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "strength": 0.7,
            },
        )
        from .remove_bg import remove_background
        return remove_background(img)
    except Exception:
        pass

    # Fallback: just generate from text
    return generate_design_from_prompt(prompt)

def render_mockup_scene(composited_image_url: str, mask_image_url: str, user_prompt: str) -> str:
    """
    Sends the composited product image and contrast mask to a remote serverless
    GPU node to paint a custom background environment based on user descriptions.
    """
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
