from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from community.models import Like
from core_store.models import Order
from generation_engine.models import DesignSession, GeneratedArt

User = get_user_model()


@staff_member_required
def dashboard_view(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # ── Stats ──────────────────────────────────────────────────
    total_users = User.objects.count()
    new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()

    total_designs = DesignSession.objects.count()
    designs_30d = DesignSession.objects.filter(created_at__gte=thirty_days_ago).count()

    total_orders = Order.objects.count()
    orders_30d = Order.objects.filter(created_at__gte=thirty_days_ago).count()

    revenue = Order.objects.aggregate(Sum("total"))["total__sum"] or 0
    revenue_30d = (
        Order.objects.filter(created_at__gte=thirty_days_ago).aggregate(Sum("total"))["total__sum"] or 0
    )

    # ── Orders by status ───────────────────────────────────────
    orders_by_status = dict(Order.objects.values_list("status").annotate(count=Count("id")))

    # ── Recent orders ─────────────────────────────────────────
    recent_orders = Order.objects.select_related("user").prefetch_related("items__art")[:5]

    # ── Recent designs ────────────────────────────────────────
    recent_designs = (
        GeneratedArt.objects.select_related("session__user")
        .order_by("-session__created_at")[:8]
    )

    # ── Designs by category ───────────────────────────────────
    CATEGORY_LABELS = dict(DesignSession.Category.choices)
    category_data = [
        {"key": c["category"], "label": CATEGORY_LABELS.get(c["category"], c["category"]), "count": c["count"]}
        for c in DesignSession.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    ]

    # ── Monthly revenue (last 12 months) ──────────────────────
    twelve_months_ago = now - timedelta(days=365)
    monthly_raw = (
        Order.objects.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total"))
        .order_by("month")
    )
    monthly_revenue = {r["month"]: float(r["total"]) for r in monthly_raw if r["month"]}

    months = []
    revs = []
    for i in range(11, -1, -1):
        m = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        label = m.strftime("%b %Y")
        months.append(label)
        revs.append(monthly_revenue.get(m, 0))
    max_rev = max(revs) if any(revs) else 1

    # ── Latest users ──────────────────────────────────────────
    latest_users = User.objects.order_by("-date_joined")[:5]

    # ── Most liked designs ────────────────────────────────────
    top_liked = (
        GeneratedArt.objects.annotate(like_count=Count("likes"))
        .select_related("session__user")
        .order_by("-like_count")[:5]
    )

    ctx = {
        "total_users": total_users,
        "new_users_30d": new_users_30d,
        "total_designs": total_designs,
        "designs_30d": designs_30d,
        "total_orders": total_orders,
        "orders_30d": orders_30d,
        "revenue": revenue,
        "revenue_30d": revenue_30d,
        "orders_by_status": orders_by_status,
        "recent_orders": recent_orders,
        "recent_designs": recent_designs,
        "category_data": category_data,
        "chart_months": months,
        "chart_revs": revs,
        "chart_max": max_rev,
        "latest_users": latest_users,
        "top_liked": top_liked,
        "now": now,
    }
    return render(request, "core_store/admin_dashboard.html", ctx)
