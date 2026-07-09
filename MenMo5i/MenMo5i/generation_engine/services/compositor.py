from PIL import Image

from generation_engine.models import ShirtTemplate

OUTPUT_SIZE = (2048, 2048)


def _open_design(source):
    if isinstance(source, Image.Image):
        return source.convert("RGBA")
    return Image.open(source).convert("RGBA")


def composite_design_on_shirt(template: ShirtTemplate, user_design, high_quality=True) -> Image.Image:
    base_shirt = Image.open(template.blank_image.path).convert("RGBA")
    design = _open_design(user_design)
    mask = Image.open(template.mask_image.path).convert("L")

    shirt_w, shirt_h = base_shirt.size

    target_w = int(shirt_w * template.canvas_width)
    target_h = int(shirt_h * template.canvas_height)
    target_x = int(shirt_w * template.canvas_x)
    target_y = int(shirt_h * template.canvas_y)

    resized = design.resize((target_w, target_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (shirt_w, shirt_h), (0, 0, 0, 0))
    canvas.paste(resized, (target_x, target_y))

    result = Image.alpha_composite(base_shirt, canvas)

    # Strip the background from the shirt photo using the binary mask.
    result.putalpha(mask)

    # Upscale the final composited output to HD resolution
    if high_quality:
        result = result.resize(OUTPUT_SIZE, Image.LANCZOS)

    return result
