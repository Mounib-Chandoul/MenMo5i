from PIL import Image, ImageFilter

try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


def remove_background(img: Image.Image) -> Image.Image:
    """
    Remove background from a design image.
    Uses rembg (AI-based) if available; falls back to smart PIL-based
    white/color removal with anti-aliased edges.
    """
    if HAS_REMBG:
        return rembg_remove(img.convert("RGBA"))

    return _remove_background_pil(img)


def _remove_background_pil(img: Image.Image) -> Image.Image:
    """
    Smart background removal using PIL only.
    Detects the dominant background color from edges and removes it
    with anti-aliased transition for clean edges.
    """
    img = img.convert("RGBA")
    orig = img.copy()

    # Sample corner colors to detect background
    w, h = img.size
    corners = [
        img.getpixel((5, 5)),
        img.getpixel((w - 5, 5)),
        img.getpixel((5, h - 5)),
        img.getpixel((w - 5, h - 5)),
    ]

    # Average the corner colors as background estimate
    bg_r = sum(c[0] for c in corners) // 4
    bg_g = sum(c[1] for c in corners) // 4
    bg_b = sum(c[2] for c in corners) // 4

    # Create a mask: pixels close to bg color become transparent
    gray = img.convert("L")
    mask = Image.new("L", (w, h), 255)
    threshold = 60

    pixels = img.load()
    mask_px = mask.load()

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            dr = abs(int(r) - bg_r)
            dg = abs(int(g) - bg_g)
            db = abs(int(b) - bg_b)
            dist = (dr * dr + dg * dg + db * db) ** 0.5
            if dist < threshold:
                # Gradual fade near the threshold for antialiasing
                if dist < threshold - 15:
                    alpha = 0
                else:
                    alpha = int(255 * (dist - (threshold - 15)) / 15)
                mask_px[x, y] = alpha

    # Blur the mask slightly for smooth edges
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))
    orig.putalpha(mask)

    return orig


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
