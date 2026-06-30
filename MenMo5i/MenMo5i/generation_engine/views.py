from django.http import JsonResponse
from .models import DesignSession, GeneratedArt


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
        status='Generated'
    )

    placeholder_shirt_graphic = "https://i.imgur.com/w3X778C.png"

    GeneratedArt.objects.create(
        session=session,
        transparent_png_url=placeholder_shirt_graphic
    )

    return JsonResponse({
        "session_id": str(session.id),
        "status": "Generated",
        "category": session.category,
        "is_public": session.is_public,
        "transparent_url": placeholder_shirt_graphic
    })
