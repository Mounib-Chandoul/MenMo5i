from PIL import Image

from generation_engine.models import ShirtTemplate

def composite_design_on_shirt(template: ShirtTemplate, user_design_path: str) -> Image.Image:
    """
    Mathematically places a transparent user graphic onto the predefined bounding coordinates
    of any structural blank shirt template image.
    """
    # 1. Open both the blank shirt template and the user's artwork
    base_shirt = Image.open(template.blank_image.path).convert("RGBA")
    design = Image.open(user_design_path).convert("RGBA")
    
    shirt_w, shirt_h = base_shirt.size
    
    # 2. Calculate the exact target pixel boundaries from the template's percentages
    target_w = int(shirt_w * template.canvas_width)
    target_h = int(shirt_h * template.canvas_height)
    target_x = int(shirt_w * template.canvas_x)
    target_y = int(shirt_h * template.canvas_y)
    
    # 3. Scale user design to match the exact allowed canvas dimensions
    # Image.Resampling.LANCZOS keeps details incredibly crisp for artwork print lines
    resized_design = design.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # 4. Create an empty transparent canvas layer matching the original shirt size
    canvas_layer = Image.new("RGBA", (shirt_w, shirt_h), (0, 0, 0, 0))
    
    # 5. Paste the scaled artwork onto the empty canvas layer at the target offsets
    canvas_layer.paste(resized_design, (target_x, target_y))
    
    # 6. Smooth alpha blend overlay layer on top of base structural shirt image
    final_composite = Image.alpha_composite(base_shirt, canvas_layer)
    
    return final_composite