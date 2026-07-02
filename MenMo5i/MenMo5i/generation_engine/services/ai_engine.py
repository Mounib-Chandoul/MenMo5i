import os

import replicate
from django.conf import settings


def _get_client():
    token = getattr(settings, 'REPLICATE_API_TOKEN', '') or os.getenv('REPLICATE_API_TOKEN', '')
    if token:
        os.environ.setdefault('REPLICATE_API_TOKEN', token)
    return replicate


def render_mockup_scene(composited_image_url: str, mask_image_url: str, user_prompt: str) -> str:
    """
    Sends the composited product image and contrast mask to a remote serverless
    GPU node to paint a custom background environment based on user descriptions.
    """
    # Using an explicit, verified production version string for SDXL Inpainting
    output = _get_client().run(
        "lucataco/sdxl-inpainting:a5b13068cc81a89a4fbeefeccc774869fcb34df4dbc92c1555e0f2771d49dde7",
        input={
            "image": composited_image_url,
            "mask": mask_image_url,
            "prompt": f"A high-end streetwear lookbook style photo of a person wearing this t-shirt, {user_prompt}, 4k, cinematic studio lighting, highly detailed structure",
            "negative_prompt": "blurry, low quality, warped artwork, distorted graphic text, low resolution, deformed face, bad anatomy",
            "num_inference_steps": 30,
            "guidance_scale": 8.0
        }
    )
    
    return output[0]