import json
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDay
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from catalog.models import Book
from cart_order.models import Order, OrderItem


PAID_STATUS = "paid"
ALLOWED_ANALYTICS_ROLES = {"admin", "support", "employee"}


def user_can_view_analytics(user):
    if not user.is_authenticated:
        return False

    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)
    role_name = getattr(role, "name", "")

    return role_name.lower() in ALLOWED_ANALYTICS_ROLES


@login_required
def analytics_dashboard_view(request):
    if not user_can_view_analytics(request.user):
        return HttpResponseForbidden("У вас нет доступа к аналитике")

    try:
        days = int(request.GET.get("days", 30))
    except (TypeError, ValueError):
        days = 30

    if days not in (7, 30, 90):
        days = 30

    date_from = timezone.now() - timedelta(days=days)

    orders_qs = Order.objects.all()
    period_orders_qs = orders_qs.filter(created_at__gte=date_from)

    paid_orders_qs = orders_qs.filter(status=PAID_STATUS)
    recent_paid_orders_qs = paid_orders_qs.filter(created_at__gte=date_from)

    money_field = DecimalField(max_digits=12, decimal_places=2)

    line_total_expr = ExpressionWrapper(
        F("quantity") * F("price_at_time"),
        output_field=money_field,
    )

    total_users = User.objects.count()
    total_books = Book.objects.count()
    total_orders = period_orders_qs.count()
    paid_orders_count = recent_paid_orders_qs.count()

    total_revenue = recent_paid_orders_qs.aggregate(
        total=Coalesce(
            Sum("total_price", output_field=money_field),
            Decimal("0.00"),
            output_field=money_field,
        )
    )["total"]

    avg_check = recent_paid_orders_qs.aggregate(
        avg=Coalesce(
            Avg("total_price", output_field=money_field),
            Decimal("0.00"),
            output_field=money_field,
        )
    )["avg"]

    orders_by_status = list(
        period_orders_qs.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    sales_by_day = list(
        recent_paid_orders_qs.annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(
            orders_count=Count("id"),
            revenue=Coalesce(
                Sum("total_price", output_field=money_field),
                Decimal("0.00"),
                output_field=money_field,
            ),
        )
        .order_by("day")
    )

    top_books = list(
        OrderItem.objects.filter(
            order__status=PAID_STATUS,
            order__created_at__gte=date_from,
        )
        .values("book__id", "book__title")
        .annotate(
            sold_qty=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(
                Sum(line_total_expr, output_field=money_field),
                Decimal("0.00"),
                output_field=money_field,
            ),
        )
        .order_by("-sold_qty", "-revenue", "book__title")[:5]
    )

    popular_genres = list(
        OrderItem.objects.filter(
            order__status=PAID_STATUS,
            order__created_at__gte=date_from,
        )
        .values("book__genres__name")
        .annotate(
            sold_qty=Coalesce(Sum("quantity"), 0),
            revenue=Coalesce(
                Sum(line_total_expr, output_field=money_field),
                Decimal("0.00"),
                output_field=money_field,
            ),
        )
        .exclude(book__genres__name__isnull=True)
        .order_by("-sold_qty", "-revenue", "book__genres__name")[:5]
    )

    latest_orders = orders_qs.select_related("user").order_by("-created_at")[:10]

    sales_labels = [item["day"].strftime("%d.%m") for item in sales_by_day]
    sales_orders_data = [item["orders_count"] for item in sales_by_day]
    sales_revenue_data = [float(item["revenue"]) for item in sales_by_day]

    status_labels = [
        item["status"] if item["status"] else "Без статуса"
        for item in orders_by_status
    ]
    status_data = [item["count"] for item in orders_by_status]

    context = {
        "days": days,
        "total_users": total_users,
        "total_books": total_books,
        "total_orders": total_orders,
        "paid_orders_count": paid_orders_count,
        "total_revenue": total_revenue,
        "avg_check": avg_check,
        "top_books": top_books,
        "popular_genres": popular_genres,
        "latest_orders": latest_orders,
        "sales_labels_json": json.dumps(sales_labels, ensure_ascii=False),
        "sales_orders_data_json": json.dumps(sales_orders_data),
        "sales_revenue_data_json": json.dumps(sales_revenue_data),
        "status_labels_json": json.dumps(status_labels, ensure_ascii=False),
        "status_data_json": json.dumps(status_data),
    }
    return render(request, "analytics_dashboard/dashboard.html", context)