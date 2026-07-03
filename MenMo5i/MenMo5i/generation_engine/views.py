import io
import os
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import DesignSession, GeneratedArt, ShirtTemplate
from .services.ai_engine import generate_design_from_prompt, generate_design_from_prompt_and_image
from .services.compositor import composite_design_on_shirt
from .services.content_filter import check_prompt


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

    # Generate design image from prompt via AI
    design_img = generate_design_from_prompt(user_prompt)
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
    context = {}

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to generate designs.")
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        user_prompt = request.POST.get('prompt', '').strip()
        logo = request.FILES.get('logo')
        inspiration = request.FILES.get('inspiration')

        if not user_prompt:
            messages.error(request, "Please provide a prompt.")
            return render(request, 'design_studio.html', context)

        result = check_prompt(user_prompt)
        if not result['allowed']:
            messages.error(request, result['reason'])
            return render(request, 'design_studio.html', context)

        # Get or generate the design image
        if logo:
            # User uploaded a final design file — use directly
            upload_dir = settings.MEDIA_ROOT / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_name = f"{uuid.uuid4().hex}_{logo.name}"
            upload_path = upload_dir / upload_name
            with open(upload_path, 'wb') as dst:
                for chunk in logo.chunks():
                    dst.write(chunk)
            design_rel_path = str(upload_path.relative_to(settings.MEDIA_ROOT))
        elif inspiration:
            # Inspiration image + prompt → AI generates a new design
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
            # Text-only — generate design from prompt via AI
            design_img = generate_design_from_prompt(user_prompt)
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
                category=request.POST.get('category', DesignSession.Category.ABSTRACT),
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
