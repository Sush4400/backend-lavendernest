"""Context processors for the LavenderNest Artisan Studio Admin."""

from django.db.models import Sum


def admin_studio_metrics(request):
    """Provides real-time studio operational metrics for the Django Admin dashboard."""
    if not request.path.startswith("/admin/"):
        return {}

    try:
        from apps.products.models import Product, ProductGroup, Category
        from apps.orders.models import Order
        from apps.users.models import Customer

        revenue = (
            Order.objects.filter(payment_status="paid").aggregate(total=Sum("total_amount"))["total"]
            or 0
        )
        low_stock_count = Product.objects.filter(stock__lte=5).count()
        low_stock_items = list(
            Product.objects.filter(stock__lte=5).values("id", "name", "sku", "stock")[:5]
        )

        return {
            "studio_metrics": {
                "total_products": Product.objects.count(),
                "active_products": Product.objects.filter(status="active").count(),
                "low_stock_products": low_stock_count,
                "low_stock_items": low_stock_items,
                "total_groups": ProductGroup.objects.count(),
                "total_categories": Category.objects.count(),
                "total_orders": Order.objects.count(),
                "pending_orders": Order.objects.filter(status="pending").count(),
                "total_revenue": revenue,
                "total_customers": Customer.objects.count(),
            }
        }
    except Exception:
        return {}

