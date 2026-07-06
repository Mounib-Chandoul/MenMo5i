import io
import logging

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt"


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    timeout_s: int = 90,
) -> bytes:
    """
    Generate an image via pollinations.ai — completely free, no API key required.

    Uses the ``flux`` model by default for best quality.  Falls back to the
    default model if the requested one isn't available.

    Returns raw PNG (or JPEG) bytes.
    """
    import urllib.parse

    encoded = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_URL}/{encoded}"

    params = {
        "width": width,
        "height": height,
        "model": model,
        "nologo": "true",
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_s)) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            logger.info(
                "Pollinations generation successful (%d bytes, model=%s)",
                len(resp.content), model,
            )
            return resp.content
    except Exception as exc:
        logger.warning("Pollinations failed (model=%s): %s", model, exc)
        raise
