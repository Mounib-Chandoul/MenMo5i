import uuid

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render

from .models import DesignSession, GeneratedArt, ShirtTemplate
from .services.compositor import composite_design_on_shirt


def trigger_generation_placeholder(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    user_prompt = (request.POST.get("prompt") or "").strip()
    if not user_prompt:
        return JsonResponse({"detail": "Prompt is required."}, status=400)

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

    placeholder_shirt_graphic = "https://i.imgur.com/w3X778C.png"

    GeneratedArt.objects.create(
        session=session,
        transparent_png_url=placeholder_shirt_graphic,
    )

    return JsonResponse({
        "session_id": str(session.id),
        "status": "Generated",
        "category": session.category,
        "is_public": session.is_public,
        "transparent_url": placeholder_shirt_graphic,
    })


def design_view(request):
    context = {}

    if request.method == 'POST':
        user_prompt = request.POST.get('prompt', '').strip()
        logo = request.FILES.get('logo')

        if not user_prompt:
            messages.error(request, "Please provide a prompt.")
            return render(request, 'design_studio.html', context)

        if not logo:
            messages.error(request, "Please upload a PNG graphic.")
            return render(request, 'design_studio.html', context)

        upload_dir = settings.MEDIA_ROOT / 'uploads'
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_name = f"{uuid.uuid4().hex}_{logo.name}"
        upload_path = upload_dir / upload_name

        with open(upload_path, 'wb') as destination:
            for chunk in logo.chunks():
                destination.write(chunk)

        template = ShirtTemplate.objects.first()
        if not template:
            messages.error(request, "No shirt template configured. Add one in the admin panel.")
            return render(request, 'design_studio.html', context)

        try:
            composited = composite_design_on_shirt(template, str(upload_path))
            output_dir = settings.MEDIA_ROOT / 'renders'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_name = f"render_{uuid.uuid4().hex}.png"
            output_path = output_dir / output_name
            composited.save(output_path)

            result_url = f"{settings.MEDIA_URL}renders/{output_name}"
            context.update({
                'status': 'success',
                'prompt_used': user_prompt,
                'result_image_url': result_url,
            })
        except Exception as exc:
            messages.error(request, f"Render failed: {exc}")

    return render(request, 'design_studio.html', context)
