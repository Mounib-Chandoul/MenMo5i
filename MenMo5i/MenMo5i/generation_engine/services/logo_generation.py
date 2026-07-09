"""
MenMo5i — Logo Generation Service
==================================

End-to-end pipeline that transforms a raw user prompt into a clean
transparent-PNG logo ready for 3D t-shirt mesh mapping.

Pipeline
--------
1. **Prompt engineering injection** — wraps the user text with vector-logo
   styling keywords so the AI model generates an isolated subject on a
   flat backdrop.
2. **AI generation** — calls the configured backend (HF / Replicate / etc.)
   and returns raw image bytes.
3. **Automated background removal** — processes the raw bytes through
   ``rembg.remove()`` entirely in-memory (no disk I/O).
4. **Storage** — wraps the transparent PNG in a Django ``ContentFile`` and
   saves it directly onto a model ``ImageField`` as ``.png``.
5. **JSON response** — returns the final relative media URL.

Dependencies (pip install)
--------------------------
    pip install Pillow rembg httpx replicate django

Usage
-----
    from generation_engine.services.logo_generation import generate_logo

    result = generate_logo(
        user_prompt="dragon silhouette",
        generation_func=my_ai_callable,
        session=design_session_instance,
    )
    # result == {
    #     "session_id": "uuid...",
    #     "status": "success",
    #     "image_url": "/media/designs/logo_abc123.png",
    # }
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Callable

from django.core.files.base import ContentFile

from .prompt_engine import build_logo_prompt
from .remove_bg import remove_background_bytes

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Prompt Engineering Injection
# ---------------------------------------------------------------------------

def inject_logo_prompt(user_prompt: str) -> str:
    """
    Wrap the user's raw text with vector-logo styling keywords.

    The injection is *appended* to the original prompt so the model still
    honours the user's intent while being guided toward a clean, isolated
    logo aesthetic with a solid backdrop.
    """
    return build_logo_prompt(user_prompt)


# ---------------------------------------------------------------------------
# 2. Automated Background Removal (Mandatory Pipeline)
# ---------------------------------------------------------------------------

def isolate_subject(image_bytes: bytes) -> bytes:
    """
    Strip the background from raw image bytes using ``rembg.remove()``.

    All processing happens strictly in-memory via ``io.BytesIO`` —
    **no intermediate file touches disk**.

    Parameters
    ----------
    image_bytes : bytes
        Raw binary payload from the AI generation API (PNG / JPEG / WebP).

    Returns
    -------
    bytes
        Clean transparent-PNG bytes.
    """
    return remove_background_bytes(image_bytes)


# ---------------------------------------------------------------------------
# 3. Storage Helpers
# ---------------------------------------------------------------------------

def save_transparent_png(
    png_bytes: bytes,
    instance,
    field_name: str = "design_image",
    filename: str | None = None,
) -> str:
    """
    Wrap transparent-PNG bytes in a Django ``ContentFile`` and save them
    directly onto a model ``ImageField``.

    Parameters
    ----------
    png_bytes : bytes
        The transparent-PNG raw bytes (output of :func:`isolate_subject`).
    instance : Model
        Any Django model instance with an ``ImageField`` (e.g. ``GeneratedArt``).
    field_name : str
        Name of the ``ImageField`` on the instance (default ``"design_image"``).
    filename : str or None
        Optional custom filename. A UUID-based name is generated when
        ``None`` (default).

    Returns
    -------
    str
        The relative media URL of the saved file (e.g. ``"/media/designs/logo_abc.png"``).
    """
    name = filename or f"logo_{uuid.uuid4().hex}.png"
    field = getattr(instance, field_name)
    field.save(name, ContentFile(png_bytes), save=True)
    url = field.url
    logger.info("Saved transparent logo → %s", url)
    return url


# ---------------------------------------------------------------------------
# 4. End-to-End Pipeline
# ---------------------------------------------------------------------------

def generate_logo(
    user_prompt: str,
    generation_func: Callable[..., bytes],
    session,
    gen_kwargs: dict | None = None,
    art_instance=None,
    field_name: str = "design_image",
) -> dict:
    """
    Execute the full logo-generation pipeline.

    Steps
    -----
    1. Inject prompt engineering keywords via :func:`inject_logo_prompt`.
    2. Call ``generation_func(injected_prompt, **gen_kwargs)`` to get raw
       image bytes from the AI backend.
    3. Remove background via :func:`isolate_subject` (rembg, in-memory).
    4. Save transparent PNG to the model ``ImageField`` via
       :func:`save_transparent_png`.
    5. Return a JSON-serialisable response dict.

    Parameters
    ----------
    user_prompt : str
        The raw text prompt provided by the user.
    generation_func : Callable[[str, ...], bytes]
        A sync (or async-compatible) callable that accepts the injected
        prompt and returns raw image bytes.
    session : DesignSession
        The database session instance. Used to create a ``GeneratedArt``
        record if ``art_instance`` is not provided. Must have a ``user``
        attribute and ``pk``.
    gen_kwargs : dict or None
        Extra keyword arguments forwarded to ``generation_func``
        (e.g. ``negative_prompt``, ``width``, ``height``).
    art_instance : Model or None
        An existing ``GeneratedArt`` instance to attach the image to.
        When ``None``, a new ``GeneratedArt`` is created for the session.
    field_name : str
        The ``ImageField`` name on the art instance (default
        ``"design_image"``).

    Returns
    -------
    dict
        ``{"session_id": str, "status": "success", "image_url": str}``
        on success, or ``{"status": "error", "error": str}`` on failure.
    """
    from generation_engine.models import GeneratedArt

    gen_kwargs = gen_kwargs or {}

    try:
        # 1 — Inject prompt
        injected = inject_logo_prompt(user_prompt)
        logger.info("Injected logo prompt: %s", injected)

        # 2 — Generate
        raw_bytes = generation_func(injected, **gen_kwargs)
        logger.info("AI generation returned %d bytes", len(raw_bytes))

        # 3 — Remove background (mandatory)
        transparent_bytes = isolate_subject(raw_bytes)
        logger.info("Background removal complete (%d bytes)", len(transparent_bytes))

        # 4 — Save to model
        if art_instance is None:
            art_instance = GeneratedArt.objects.create(session=session)

        relative_path = save_transparent_png(
            transparent_bytes,
            art_instance,
            field_name=field_name,
        )

        return {
            "session_id": str(session.pk),
            "status": "success",
            "image_url": relative_path,
        }

    except Exception as exc:
        logger.exception("Logo generation failed for prompt=%r", user_prompt)
        return {
            "status": "error",
            "error": str(exc),
        }
