import io
import logging
import random
import time

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt"
MAX_RETRIES = 3
BASE_DELAY_S = 2.0


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = "",
    timeout_s: int = 120,
) -> bytes:
    """
    Generate an image via pollinations.ai — completely free, no API key required.

    Retries up to ``MAX_RETRIES`` times with exponential back-off to handle
    transient 5xx errors or connection resets from the free tier.

    Omits the ``model`` parameter by default to let Pollinations choose the
    best available model (avoids 500 errors from unavailable model names).

    Returns raw image bytes (JPEG or PNG depending on what the service sends).

    Raises
    ------
    RuntimeError
        After all retries are exhausted.
    """
    import urllib.parse

    encoded = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_URL}/{encoded}"

    params: dict[str, str | int] = {
        "width": width,
        "height": height,
        "nologo": "true",
    }
    if model:
        params["model"] = model

    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_s)) as client:
                resp = client.get(url, params=params)

                if resp.status_code == 200:
                    logger.info(
                        "Pollinations generation successful (%d bytes)%s",
                        len(resp.content),
                        f" (model={model})" if model else "",
                    )
                    return resp.content

                # Transient server error — retry
                logger.warning(
                    "Pollinations returned %d (attempt %d/%d)",
                    resp.status_code, attempt, MAX_RETRIES,
                )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            logger.warning(
                "Pollinations connection error (attempt %d/%d): %s",
                attempt, MAX_RETRIES, exc,
            )

        # Back-off before next retry
        if attempt < MAX_RETRIES:
            delay = BASE_DELAY_S * (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(delay)

    raise RuntimeError(
        f"Pollinations image generation failed after {MAX_RETRIES} retries."
    ) from last_exc
