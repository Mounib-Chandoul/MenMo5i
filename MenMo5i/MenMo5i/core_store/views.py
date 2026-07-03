import io
import os
import tempfile
import urllib.request

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from PIL import Image

from generation_engine.models import DesignSession, GeneratedArt, ShirtTemplate
from generation_engine.services.compositor import composite_design_on_shirt

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
    session = get_object_or_404(
        DesignSession.objects.select_related('user').prefetch_related('artworks'),
        id=session_id,
        is_public=True,
    )
    return render(request, 'core_store/design_detail.html', {
        'session': session,
    })


@require_POST
@login_required
def add_to_cart_view(request, art_id):
    art = get_object_or_404(GeneratedArt, id=art_id)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        art=art,
        defaults={'quantity': 1},
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=['quantity'])
    messages.success(request, 'Design added to cart.')
    return redirect(request.POST.get('next', 'cart'))


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
