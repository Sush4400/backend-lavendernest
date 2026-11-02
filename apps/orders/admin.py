"""Django Admin for the orders app."""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "product_name", "product_sku", "unit_price", "quantity", "line_total_display")
    readonly_fields = ("product", "product_name", "product_sku", "unit_price", "quantity", "line_total_display")
    can_delete = False

    def line_total_display(self, obj):
        return f"₹{obj.line_total}"
    line_total_display.short_description = "Line Total"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "customer_display", "status_badge", "payment_badge",
        "items_count", "total_display", "created_at",
    )
    list_filter = ("status", "payment_status", "created_at", "shipping_country")
    search_fields = ("order_number", "customer__user__email", "shipping_full_name", "tracking_number")
    readonly_fields = (
        "id", "order_number", "customer", "subtotal", "shipping_cost",
        "discount_amount", "tax_amount", "total_amount",
        "payment_status", "created_at", "updated_at",
    )
    inlines = [OrderItemInline]
    ordering = ["-created_at"]
    actions = ["mark_as_confirmed", "mark_as_shipped", "mark_as_delivered", "mark_as_cancelled"]

    fieldsets = (
        ("Order Overview", {
            "fields": ("id", "order_number", "customer", "status", "payment_status"),
        }),
        ("Recipient & Shipping Details", {
            "fields": (
                "shipping_full_name", "shipping_phone",
                "shipping_address_line1", "shipping_address_line2",
                "shipping_city", "shipping_state", "shipping_postal_code", "shipping_country",
            ),
        }),
        ("Financial Summary", {
            "fields": ("subtotal", "shipping_cost", "discount_amount", "tax_amount", "total_amount"),
        }),
        ("Fulfillment & Notes", {
            "fields": ("tracking_number", "notes"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def customer_display(self, obj):
        url = reverse("admin:users_customer_change", args=[obj.customer.id])
        return format_html(
            '<a href="{}" style="font-weight: 500;">{}</a>',
            url, obj.customer.user.email,
        )
    customer_display.short_description = "Customer"

    def items_count(self, obj):
        count = obj.items.count()
        return f"{count} item{'s' if count != 1 else ''}"
    items_count.short_description = "Items"

    def total_display(self, obj):
        return format_html('<strong style="color: #4a2469; font-size: 13.5px;">₹{}</strong>', obj.total_amount)
    total_display.short_description = "Total"

    def status_badge(self, obj):
        colors = {
            Order.Status.PENDING: "#f39c12",
            Order.Status.CONFIRMED: "#3498db",
            Order.Status.PROCESSING: "#9b59b6",
            Order.Status.SHIPPED: "#8e44ad",
            Order.Status.DELIVERED: "#2ecc71",
            Order.Status.CANCELLED: "#e74c3c",
        }
        color = colors.get(obj.status, "#bdc3c7")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-weight:600;font-size:11px;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Order Status"

    def payment_badge(self, obj):
        colors = {
            Order.PaymentStatus.PENDING: "#f39c12",
            Order.PaymentStatus.PAID: "#2ecc71",
            Order.PaymentStatus.FAILED: "#e74c3c",
            Order.PaymentStatus.REFUNDED: "#95a5a6",
        }
        color = colors.get(obj.payment_status, "#bdc3c7")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-weight:600;font-size:11px;">{}</span>',
            color, obj.get_payment_status_display(),
        )
    payment_badge.short_description = "Payment Status"

    def mark_as_confirmed(self, request, queryset):
        rows = queryset.update(status=Order.Status.CONFIRMED)
        self.message_user(request, f"{rows} orders marked as Confirmed.", messages.SUCCESS)
    mark_as_confirmed.short_description = "Mark selected as Confirmed"

    def mark_as_shipped(self, request, queryset):
        rows = queryset.update(status=Order.Status.SHIPPED)
        self.message_user(request, f"{rows} orders marked as Shipped.", messages.SUCCESS)
    mark_as_shipped.short_description = "Mark selected as Shipped"

    def mark_as_delivered(self, request, queryset):
        rows = queryset.update(status=Order.Status.DELIVERED)
        self.message_user(request, f"{rows} orders marked as Delivered.", messages.SUCCESS)
    mark_as_delivered.short_description = "Mark selected as Delivered"

    def mark_as_cancelled(self, request, queryset):
        rows = queryset.update(status=Order.Status.CANCELLED)
        self.message_user(request, f"{rows} orders marked as Cancelled.", messages.WARNING)
    mark_as_cancelled.short_description = "Mark selected as Cancelled"

    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if obj and not request.user.is_superuser:
            base.append("status")
        return base

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "product_sku", "unit_price", "quantity")
    search_fields = ("product_name", "product_sku", "order__order_number")
    readonly_fields = ("order", "product", "product_name", "product_sku", "unit_price", "quantity")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
