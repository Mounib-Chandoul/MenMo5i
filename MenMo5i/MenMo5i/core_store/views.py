import io
import os
import tempfile
import urllib.request
import uuid

import concurrent.futures

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef
from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from PIL import Image

from community.models import Follow, Like
from generation_engine.models import DesignSession, GeneratedArt, ShirtTemplate
from generation_engine.services.ai_engine import generate_design_from_prompt_and_image
from generation_engine.services.compositor import composite_design_on_shirt
from generation_engine.views import _save_design_image

from .models import CartItem, Order, OrderItem


PRINT_DPI = 300
PRINT_W = 3600
PRINT_H = 4500


def _open_design_image(art):
    """Return PIL Image from local design_image file, or fall back to fetching via URL."""
    if art.design_image:
        try:
            return Image.open(art.design_image.path).convert("RGBA")
        except Exception:
            pass
    try:
        resp = urllib.request.urlopen(art.transparent_png_url, timeout=15)
        return Image.open(io.BytesIO(resp.read())).convert("RGBA")
    except Exception:
        raise


def export_design_view(request, session_id):
    session = get_object_or_404(
        DesignSession.objects.prefetch_related('artworks'),
        id=session_id,
        is_public=True,
    )
    art = session.artworks.first()
    if not art:
        return HttpResponseNotFound("No artwork available for this design.")

    try:
        design = _open_design_image(art)
    except Exception:
        return HttpResponseNotFound("Could not load the design image.")

    design.thumbnail((PRINT_W, PRINT_H), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (PRINT_W, PRINT_H), (0, 0, 0, 0))
    x = (PRINT_W - design.width) // 2
    y = (PRINT_H - design.height) // 2
    canvas.paste(design, (x, y), design)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return FileResponse(buf, as_attachment=True,
                        filename=f"{session.id}_design_300dpi.png")


def export_shirt_view(request, session_id):
    session = get_object_or_404(
        DesignSession.objects.prefetch_related('artworks'),
        id=session_id,
        is_public=True,
    )
    art = session.artworks.first()
    if not art:
        return HttpResponseNotFound("No artwork available for this design.")

    template = ShirtTemplate.objects.first()
    if not template:
        return HttpResponseNotFound("No shirt template configured. Contact admin.")

    try:
        design = _open_design_image(art)
    except Exception:
        return HttpResponseNotFound("Could not load the design image.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    design.save(tmp, format="PNG")
    tmp.close()

    try:
        composited = composite_design_on_shirt(template, tmp.name, high_quality=True)
        composited = composited.convert("RGB")
        composited = composited.resize((PRINT_W, PRINT_H), Image.Resampling.LANCZOS)
    finally:
        os.unlink(tmp.name)

    buf = io.BytesIO()
    composited.save(buf, format="PNG")
    buf.seek(0)
    return FileResponse(buf, as_attachment=True,
                        filename=f"{session.id}_shirt_preview_300dpi.png")


def landing_page_view(request):
    return render(request, 'core_store/landing.html')


def design_detail_view(request, session_id):
    qs = DesignSession.objects.select_related('user').prefetch_related('artworks')
    if request.user.is_authenticated:
        qs = qs.annotate(
            like_count=Count('artworks__likes', distinct=True),
            is_liked=Exists(
                Like.objects.filter(user=request.user, art__session=OuterRef('pk'))
            ),
        )
    else:
        qs = qs.annotate(
            like_count=Count('artworks__likes', distinct=True),
        )
    session = get_object_or_404(qs, id=session_id, is_public=True)
    return render(request, 'core_store/design_detail.html', {
        'session': session,
    })


@login_required
def my_designs_view(request):
    sessions = DesignSession.objects.filter(user=request.user).select_related('user').prefetch_related('artworks').annotate(
        like_count=Count('artworks__likes', distinct=True),
    ).order_by('-created_at')
    return render(request, 'core_store/my_designs.html', {
        'sessions': sessions,
    })


@login_required
def remix_design_view(request, session_id):
    original = get_object_or_404(DesignSession, id=session_id, is_public=True)
    if request.method == 'POST':
        new_prompt = (request.POST.get('prompt') or original.raw_prompt).strip()
        from generation_engine.services.content_filter import check_prompt
        result = check_prompt(new_prompt)
        if not result['allowed']:
            messages.error(request, result['reason'])
            return redirect('design_detail', session_id=session_id)

        from generation_engine.services.ai_engine import generate_design_from_prompt
        design_img = generate_design_from_prompt(new_prompt)
        from generation_engine.views import _save_design_image
        design_rel_path = _save_design_image(design_img, new_prompt)

        template = ShirtTemplate.objects.first()
        if template:
            design_path = os.path.join(settings.MEDIA_ROOT, design_rel_path)
            composited = composite_design_on_shirt(template, design_path)
            output_dir = settings.MEDIA_ROOT / 'renders'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_name = f"render_{uuid.uuid4().hex}.png"
            output_path = output_dir / output_name
            composited.save(output_path)

            new_session = DesignSession.objects.create(
                user=request.user,
                raw_prompt=new_prompt,
                category=original.category,
                is_public=True,
                status='Generated',
            )
            GeneratedArt.objects.create(
                session=new_session,
                design_image=design_rel_path,
                transparent_png_url='',
            )
            messages.success(request, 'Remix created successfully!')
            return redirect('design_detail', session_id=new_session.id)
        else:
            messages.error(request, "No shirt template configured.")
            return redirect('design_detail', session_id=session_id)
    return render(request, 'core_store/remix.html', {
        'original': original,
    })


VARIATION_SUFFIXES = [
    'bold and striking version',
    'minimal and clean version',
    'dark and moody version',
    'colorful vibrant version',
]


@login_required
def variations_view(request, session_id):
    original = get_object_or_404(
        DesignSession.objects.prefetch_related('artworks'),
        id=session_id,
        is_public=True,
    )
    art = original.artworks.first()
    if not art:
        messages.error(request, 'No artwork to generate variations from.')
        return redirect('design_detail', session_id=session_id)

    try:
        design_img = _open_design_image(art)
    except Exception as e:
        messages.error(request, f'Could not load design image: {e}')
        return redirect('design_detail', session_id=session_id)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    design_img.save(tmp, format='PNG')
    tmp.close()

    def _generate_variation(index):
        suffix = VARIATION_SUFFIXES[index % len(VARIATION_SUFFIXES)]
        var_prompt = f"{original.raw_prompt}, {suffix}"
        try:
            var_img = generate_design_from_prompt_and_image(var_prompt, tmp.name)
            design_path = _save_design_image(var_img, var_prompt)
            var_template = ShirtTemplate.objects.first()
            if var_template:
                var_design_full = os.path.join(settings.MEDIA_ROOT, design_path)
                composited = composite_design_on_shirt(var_template, var_design_full)
                out_dir = settings.MEDIA_ROOT / 'renders'
                out_dir.mkdir(parents=True, exist_ok=True)
                out_name = f"var_{uuid.uuid4().hex}.png"
                out_path = out_dir / out_name
                composited.save(out_path)

                new_session = DesignSession.objects.create(
                    user=request.user,
                    raw_prompt=var_prompt,
                    category=original.category,
                    is_public=True,
                    status='Generated',
                )
                new_art = GeneratedArt.objects.create(
                    session=new_session,
                    design_image=design_path,
                    transparent_png_url='',
                )
                return new_session
        except Exception:
            pass
        return None

    variations = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_generate_variation, i) for i in range(4)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                variations.append(result)

    os.unlink(tmp.name)

    if not variations:
        messages.error(request, 'Could not generate any variations. Try again later.')
        return redirect('design_detail', session_id=session_id)

    return render(request, 'core_store/variations.html', {
        'original': original,
        'variations': variations,
    })


@require_POST
@login_required
def add_to_cart_view(request, art_id):
    art = get_object_or_404(GeneratedArt, id=art_id)
    size = (request.POST.get('size') or CartItem.Size.M).lower()
    color = (request.POST.get('color') or CartItem.Color.BLACK).lower()
    valid_sizes = {s[0] for s in CartItem.Size.choices}
    valid_colors = {c[0] for c in CartItem.Color.choices}
    if size not in valid_sizes:
        size = CartItem.Size.M
    if color not in valid_colors:
        color = CartItem.Color.BLACK
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        art=art,
        size=size,
        color=color,
        defaults={'quantity': 1},
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=['quantity'])
    messages.success(request, 'Design added to cart.')
    return redirect(request.POST.get('next', 'cart'))


@require_POST
@login_required
def update_cart_quantity_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    try:
        qty = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        qty = 1
    if qty < 1:
        cart_item.delete()
        messages.success(request, 'Item removed.')
    else:
        cart_item.quantity = min(qty, 99)
        cart_item.save(update_fields=['quantity'])
        messages.success(request, 'Quantity updated.')
    return redirect('cart')


@require_POST
@login_required
def remove_from_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


@login_required
def checkout_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('art__session__user')
    if not cart_items:
        messages.error(request, 'Cart is empty.')
        return redirect('cart')

    total = sum(item.total_price for item in cart_items)

    if request.method == 'POST':
        shipping_name = (request.POST.get('shipping_name') or '').strip()
        shipping_address = (request.POST.get('shipping_address') or '').strip()
        shipping_city = (request.POST.get('shipping_city') or '').strip()
        shipping_phone = (request.POST.get('shipping_phone') or '').strip()
        payment_method = request.POST.get('payment_method') or 'cod'
        notes = (request.POST.get('notes') or '').strip()

        if not all([shipping_name, shipping_address, shipping_city, shipping_phone]):
            messages.error(request, 'Please fill in all shipping fields.')
            return render(request, 'core_store/checkout.html', {
                'cart': cart_items,
                'cart_total': total,
            })

        order = Order.objects.create(
            user=request.user,
            total=total,
            shipping_name=shipping_name,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_phone=shipping_phone,
            payment_method=payment_method,
            notes=notes,
            status=Order.Status.PENDING,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                art=item.art,
                quantity=item.quantity,
                price=item.art.price,
                size=item.size,
                color=item.color,
            )

        cart_items.delete()

        messages.success(request, f'Order #{order.pk} placed successfully!')
        return redirect('order_confirmation', order_id=order.pk)

    return render(request, 'core_store/checkout.html', {
        'cart': cart_items,
        'cart_total': total,
    })


@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'core_store/order_confirmation.html', {
        'order': order,
    })


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__art__session')
    return render(request, 'core_store/order_history.html', {
        'orders': orders,
    })


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__art__session__user'),
        id=order_id,
        user=request.user,
    )
    return render(request, 'core_store/order_detail.html', {
        'order': order,
    })
