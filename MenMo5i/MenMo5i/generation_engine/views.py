import io
import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from asgiref.sync import sync_to_async

from .models import DesignSession, GeneratedArt, SavedPrompt, ShirtTemplate
from .services.ai_engine import generate_design_from_prompt, generate_design_from_prompt_and_image
from .services.compositor import composite_design_on_shirt
from .services.content_filter import check_prompt
from .services.hf_inference import (
    async_generate_image_from_prompt,
    save_to_model_field,
)
from .services.prompt_engine import enhance_prompt, NEGATIVE_PROMPT


STYLE_PRESETS = [
    {'key': 'none', 'label': 'None', 'suffix': ''},
    {'key': 'cyberpunk', 'label': 'Cyberpunk', 'suffix': 'cyberpunk style, neon colors, dark background, futuristic, tech patterns'},
    {'key': 'minimal', 'label': 'Minimal', 'suffix': 'minimalist style, clean lines, simple shapes, negative space, monochrome palette'},
    {'key': 'vintage', 'label': 'Vintage', 'suffix': 'vintage retro style, distressed, worn look, 80s aesthetic, faded colors'},
    {'key': 'tribal', 'label': 'Tribal', 'suffix': 'tribal patterns, geometric, african inspired, bold symmetrical shapes, cultural motifs'},
    {'key': 'neon', 'label': 'Neon', 'suffix': 'neon glow style, vibrant bright colors, glowing outlines, dark background, electric'},
    {'key': 'graffiti', 'label': 'Graffiti', 'suffix': 'graffiti street art style, spray paint texture, wild style lettering, urban'},
    {'key': 'abstract', 'label': 'Abstract', 'suffix': 'abstract geometric art, fluid shapes, gradient colors, modern art style'},
]


def _save_design_image(pil_image, prompt):
    """Save a PIL Image to the designs storage and return the relative path."""
    name = f"design_{uuid.uuid4().hex}.png"
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    path = default_storage.save(f"designs/{name}", ContentFile(buf.getvalue()))
    return path


def trigger_generation_placeholder(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    user_prompt = (request.POST.get("prompt") or "").strip()
    if not user_prompt:
        return JsonResponse({"detail": "Prompt is required."}, status=400)

    result = check_prompt(user_prompt)
    if not result['allowed']:
        return JsonResponse({"detail": result['reason']}, status=400)

    raw_category = (request.POST.get("category") or DesignSession.Category.ABSTRACT).strip().lower()
    category_values = {choice[0] for choice in DesignSession.Category.choices}
    category = raw_category if raw_category in category_values else DesignSession.Category.ABSTRACT
    is_public = request.POST.get("is_public") != "0"

    session = DesignSession.objects.create(
        user=request.user,
        raw_prompt=user_prompt,
        category=category,
        is_public=is_public,
        status='Generated',
    )

    design_img = generate_design_from_prompt(user_prompt, category=category)
    design_path = _save_design_image(design_img, user_prompt)

    art = GeneratedArt.objects.create(
        session=session,
        design_image=design_path,
        transparent_png_url='',
    )

    return JsonResponse({
        "session_id": str(session.id),
        "status": "Generated",
        "category": session.category,
        "is_public": session.is_public,
        "image_url": art.image_url,
    })


def design_view(request):
    context = {
        'style_presets': STYLE_PRESETS,
    }

    if request.user.is_authenticated:
        context['saved_prompts'] = SavedPrompt.objects.filter(user=request.user)[:20]

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to generate designs.")
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        user_prompt = request.POST.get('prompt', '').strip()
        logo = request.FILES.get('logo')
        inspiration = request.FILES.get('inspiration')
        save_prompt = request.POST.get('save_prompt') == '1'

        if not user_prompt:
            messages.error(request, "Please provide a prompt.")
            return render(request, 'design_studio.html', context)

        result = check_prompt(user_prompt)
        if not result['allowed']:
            messages.error(request, result['reason'])
            return render(request, 'design_studio.html', context)

        if save_prompt and request.user.is_authenticated:
            SavedPrompt.objects.get_or_create(
                user=request.user,
                prompt=user_prompt,
                defaults={'category': request.POST.get('category', DesignSession.Category.ABSTRACT)},
            )

        raw_category = (request.POST.get("category") or DesignSession.Category.ABSTRACT).strip().lower()
        category_values = {c[0] for c in DesignSession.Category.choices}
        category = raw_category if raw_category in category_values else DesignSession.Category.ABSTRACT

        if logo:
            upload_dir = settings.MEDIA_ROOT / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_name = f"{uuid.uuid4().hex}_{logo.name}"
            upload_path = upload_dir / upload_name
            with open(upload_path, 'wb') as dst:
                for chunk in logo.chunks():
                    dst.write(chunk)
            design_rel_path = str(upload_path.relative_to(settings.MEDIA_ROOT))
        elif inspiration:
            upload_dir = settings.MEDIA_ROOT / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            insp_name = f"insp_{uuid.uuid4().hex}_{inspiration.name}"
            insp_path = upload_dir / insp_name
            with open(insp_path, 'wb') as dst:
                for chunk in inspiration.chunks():
                    dst.write(chunk)
            design_img = generate_design_from_prompt_and_image(user_prompt, str(insp_path))
            design_rel_path = _save_design_image(design_img, user_prompt)
        else:
            design_img = generate_design_from_prompt(user_prompt, category=category)
            design_rel_path = _save_design_image(design_img, user_prompt)

        template = ShirtTemplate.objects.first()
        if not template:
            messages.error(request, "No shirt template configured. Add one in the admin panel.")
            return render(request, 'design_studio.html', context)

        try:
            design_path = os.path.join(settings.MEDIA_ROOT, design_rel_path)
            composited = composite_design_on_shirt(template, design_path)
            output_dir = settings.MEDIA_ROOT / 'renders'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_name = f"render_{uuid.uuid4().hex}.png"
            output_path = output_dir / output_name
            composited.save(output_path)

            session = DesignSession.objects.create(
                user=request.user,
                raw_prompt=user_prompt,
                category=category,
                is_public=True,
                status='Generated',
            )

            art = GeneratedArt.objects.create(
                session=session,
                design_image=f"renders/{output_name}",
                transparent_png_url='',
            )

            messages.success(request, "Design generated successfully!")
            return redirect('design_detail', session_id=session.id)

        except Exception as exc:
            messages.error(request, f"Render failed: {exc}")
            return render(request, 'design_studio.html', context)

    return render(request, 'design_studio.html', context)


@login_required
@require_POST
def save_prompt_view(request):
    prompt = (request.POST.get('prompt') or '').strip()
    category = (request.POST.get('category') or DesignSession.Category.ABSTRACT).strip().lower()
    if prompt:
        SavedPrompt.objects.get_or_create(
            user=request.user,
            prompt=prompt,
            defaults={'category': category},
        )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'detail': 'Prompt required'}, status=400)


@login_required
def saved_prompts_json(request):
    prompts = SavedPrompt.objects.filter(user=request.user).values('id', 'prompt', 'category', 'created_at')
    return JsonResponse({'prompts': list(prompts)})


@require_POST
@login_required
def delete_saved_prompt_view(request, prompt_id):
    SavedPrompt.objects.filter(id=prompt_id, user=request.user).delete()
    return JsonResponse({'status': 'ok'})


# ---------------------------------------------------------------------------
# Hugging Face Serverless Inference view
# ---------------------------------------------------------------------------

async def hf_generate_view(request):
    """
    Fully async view — calls Hugging Face Serverless Inference API (SDXL)
    without blocking the main thread.

    POST payload::

        prompt       (required) — text description
        category     (optional) — design category
        is_public    (optional) — "0" or "1" (default "1")
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON body."}, status=400)
        user_prompt = (data.get("prompt") or "").strip()
        raw_category = (data.get("category") or "").strip().lower()
        is_public = data.get("is_public", "1") != "0"
    else:
        user_prompt = (request.POST.get("prompt") or "").strip()
        raw_category = (request.POST.get("category") or "").strip().lower()
        is_public = request.POST.get("is_public") != "0"

    if not user_prompt:
        return JsonResponse({"detail": "Prompt is required."}, status=400)

    result = await sync_to_async(check_prompt)(user_prompt)
    if not result["allowed"]:
        return JsonResponse({"detail": result["reason"]}, status=400)

    category_values = {c[0] for c in DesignSession.Category.choices}
    category = raw_category if raw_category in category_values else DesignSession.Category.ABSTRACT

    enhanced_prompt = enhance_prompt(user_prompt, category=category)
    logger.info("Enhanced prompt for HF view: %s", enhanced_prompt)

    try:
        image_bytes = await async_generate_image_from_prompt(
            enhanced_prompt,
            negative_prompt=NEGATIVE_PROMPT,
        )
    except RuntimeError as exc:
        logger.exception("HF image generation failed for prompt=%r", user_prompt)
        return JsonResponse({"detail": str(exc)}, status=502)

    session = await sync_to_async(DesignSession.objects.create)(
        user=request.user,
        raw_prompt=user_prompt,
        category=category,
        is_public=is_public,
        status="Generated",
    )

    art = await sync_to_async(GeneratedArt.objects.create)(
        session=session,
        design_image=None,
        transparent_png_url="",
    )

    path = await sync_to_async(save_to_model_field)(
        image_bytes, art, field_name="design_image",
    )

    return JsonResponse({
        "session_id": str(session.id),
        "status": "Generated",
        "category": session.category,
        "is_public": session.is_public,
        "image_url": art.image_url,
        "storage_path": path,
    })
