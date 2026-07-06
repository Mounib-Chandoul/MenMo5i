"""
Hugging Face Inference Providers — async text-to-image generation.

Connects via ``router.huggingface.co`` to Hugging Face's Inference Providers
infrastructure, handles cold-starts, rate-limits, and network timeouts with
exponential-backoff retries, and persists the raw binary payload into Django's
default storage or directly onto a model ``ImageField``.
"""

from __future__ import annotations

import asyncio
import logging
import random
from uuid import uuid4

import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HF_ROUTER = "https://router.huggingface.co"
HF_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
# Use the hf-inference route (HF's own serverless infra on the new router)
HF_API_URL = f"{HF_ROUTER}/hf-inference/models/{HF_MODEL}"

MAX_RETRIES = 5
BASE_DELAY_S = 1.0
MAX_DELAY_S = 30.0
REQUEST_TIMEOUT_S = 120


def _get_token() -> str:
    token = getattr(settings, "HF_API_TOKEN", None)
    if not token:
        from os import getenv as _getenv
        token = _getenv("HF_API_TOKEN", "")
    if not token:
        raise RuntimeError(
            "HF_API_TOKEN is not configured. Set it in Django settings or "
            "the .env file."
        )
    return token


# ---------------------------------------------------------------------------
# Core async generator
# ---------------------------------------------------------------------------

async def async_generate_image_from_prompt(
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 1024,
    height: int = 1024,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
) -> bytes:
    """
    Send a text prompt to Hugging Face Inference Providers (router) and return
    raw PNG bytes.

    Retries on:
    * ``503`` — cold-start / overloaded
    * ``429`` / ``529`` — rate-limited
    * ``200`` with JSON body — model still loading
    * Network timeouts / transient ``httpx`` errors

    Raises ``RuntimeError`` after exhausting all retries.
    """
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "image/png,*/*;q=0.9",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt or "",
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        },
    }

    last_exception: Exception | None = None

    async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT_S)) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(HF_API_URL, headers=headers, json=payload)

                # ── 200 : check content-type ──────────────────────────
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        return response.content

                    try:
                        body = response.json()
                    except Exception:
                        body = {}

                    error_msg = body.get("error", "")
                    estimated = body.get("estimated_time", BASE_DELAY_S)

                    if "loading" in error_msg.lower():
                        delay = min(float(estimated), MAX_DELAY_S)
                        logger.warning(
                            "HF model still loading (attempt %d/%d). "
                            "Waiting %.1f s …", attempt, MAX_RETRIES, delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    raise RuntimeError(
                        f"HF API returned 200 but content is not an image. "
                        f"Content-Type={content_type!r} Body={body!r}"
                    )

                # ── 403 forbidden (bad token / permissions) ───────────
                if response.status_code == 403:
                    error_body = _try_decode(response)
                    raise RuntimeError(
                        "HF API 403 Forbidden — your HF_API_TOKEN lacks "
                        "'Make calls to Inference Providers' permission. "
                        "Create a new fine-grained token at:\n"
                        "  https://huggingface.co/settings/tokens/new"
                        "?ownUserPermissions=inference.serverless.write"
                        "&tokenType=fineGrained\n"
                        f"Details: {error_body}"
                    )

                # ── 503 (cold-start / overloaded) ─────────────────────
                if response.status_code == 503:
                    delay = _backoff_delay(attempt, response)
                    logger.warning(
                        "HF API 503 (attempt %d/%d). Retrying in %.1f s …",
                        attempt, MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                # ── 429 / 529 (rate-limit / overloaded) ───────────────
                if response.status_code in (429, 529):
                    delay = _backoff_delay(attempt, response)
                    logger.warning(
                        "HF API %d (attempt %d/%d). Retrying in %.1f s …",
                        response.status_code, attempt, MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                # ── Any other non-2xx ──────────────────────────────────
                detail = _try_decode(response)
                raise RuntimeError(
                    f"HF API responded with {response.status_code}: {detail}"
                )

            except httpx.TimeoutException as exc:
                last_exception = exc
                delay = _backoff_delay(attempt)
                logger.warning(
                    "HF API timeout (attempt %d/%d). Retrying in %.1f s …",
                    attempt, MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)

            except httpx.RequestError as exc:
                last_exception = exc
                delay = _backoff_delay(attempt)
                logger.warning(
                    "HF API request error (attempt %d/%d): %s. Retrying in %.1f s …",
                    attempt, MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Image generation failed after {MAX_RETRIES} retries."
    ) from last_exception


def _try_decode(response: httpx.Response) -> str:
    try:
        return str(response.json())
    except Exception:
        return response.text[:500]


def _backoff_delay(attempt: int, response: httpx.Response | None = None) -> float:
    """Exponential back-off with jitter, respecting Retry-After header."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return min(float(retry_after), MAX_DELAY_S)
            except ValueError:
                pass
    delay = BASE_DELAY_S * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
    return min(delay, MAX_DELAY_S)


def _backoff_delay(attempt: int, response: httpx.Response | None = None) -> float:
    """Exponential back-off with jitter, respecting Retry-After header."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return min(float(retry_after), MAX_DELAY_S)
            except ValueError:
                pass
    delay = BASE_DELAY_S * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
    return min(delay, MAX_DELAY_S)


# ---------------------------------------------------------------------------
# Synchronous convenience wrapper
# ---------------------------------------------------------------------------

def generate_image_from_prompt(
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 1024,
    height: int = 1024,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
) -> bytes:
    """Synchronous wrapper around :func:`async_generate_image_from_prompt`."""
    return asyncio.run(
        async_generate_image_from_prompt(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
    )


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def store_image_bytes(
    image_bytes: bytes,
    subdir: str = "generated/hf",
    filename: str | None = None,
) -> str:
    """
    Persist raw image bytes to the configured ``DEFAULT_FILE_STORAGE`` and
    return the relative media path.

    Example::

        >>> path = store_image_bytes(png_data)
        >>> path
        'generated/hf/a1b2c3d4e5f6.png'
        >>> default_storage.url(path)
        '/media/generated/hf/a1b2c3d4e5f6.png'
    """
    name = filename or f"hf_{uuid4().hex}.png"
    saved_path = default_storage.save(f"{subdir}/{name}", ContentFile(image_bytes))
    logger.info("Saved generated image → %s", saved_path)
    return saved_path


def save_to_model_field(
    image_bytes: bytes,
    instance: object,
    field_name: str = "design_image",
    filename: str | None = None,
) -> str:
    """
    Store image bytes directly onto an ``ImageField``, persist the model,
    and return the relative storage path.

    Usage::

        >>> art = GeneratedArt.objects.create(session=session)
        >>> path = save_to_model_field(png_data, art, field_name="design_image")
    """
    name = filename or f"hf_{uuid4().hex}.png"
    field = getattr(instance, field_name)
    field.save(name, ContentFile(image_bytes), save=True)
    logger.info("Saved image to %s.%s (pk=%s)", type(instance).__name__, field_name, instance.pk)
    return field.name
