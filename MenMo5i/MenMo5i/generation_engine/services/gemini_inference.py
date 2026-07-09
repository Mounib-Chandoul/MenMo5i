import base64
import io
import logging

import httpx
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def generate_image(prompt: str, image_path: str | None = None) -> bytes:
    """Generate an image via Gemini 2.0 Flash.

    If *image_path* is provided it is sent alongside the text prompt as a
    multimodal (image-to-image) request.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured in settings / .env")

    url = f"{GEMINI_API_URL}?key={api_key}"

    parts = [{"text": prompt}]
    if image_path:
        with open(image_path, "rb") as f:
            raw = f.read()
        ext = image_path.rsplit(".", 1)[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        parts.append({
            "inlineData": {
                "mimeType": mime,
                "data": base64.b64encode(raw).decode(),
            },
        })

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 1.0,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 8192,
            "responseModalities": ["Text", "Image"],
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ],
    }

    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        finish_reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini blocked the request: {finish_reason}")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            b64_data = part["inlineData"]["data"]
            return base64.b64decode(b64_data)

    text_parts = [p.get("text", "") for p in parts if "text" in p]
    raise RuntimeError(
        f"Gemini returned no image data. Text response: {' '.join(text_parts)}"
    )
