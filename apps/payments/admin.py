"""Django Admin for the payments app."""

from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "provider", "status_badge", "amount_display",
        "amount_refunded", "razorpay_payment_id", "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = (
        "order__order_number", "razorpay_payment_id",
        "razorpay_order_id", "order__customer__user__email",
    )
    readonly_fields = (
        "id", "order", "razorpay_order_id", "razorpay_payment_id",
        "razorpay_signature", "amount", "currency", "gateway_response",
        "created_at", "updated_at",
    )
    ordering = ["-created_at"]

    fieldsets = (
        ("Payment Info", {
            "fields": ("id", "order", "provider", "status"),
        }),
        ("Razorpay", {
            "fields": ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature"),
        }),
        ("Financials", {
            "fields": ("amount", "currency", "amount_refunded"),
        }),
        ("Gateway Response", {
            "fields": ("gateway_response",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = "Order"

    def status_badge(self, obj):
        colors = {
            "captured": "#2ecc71",
            "failed": "#e74c3c",
            "refunded": "#95a5a6",
            "created": "#f39c12",
            "authorized": "#3498db",
        }
        color = colors.get(obj.status, "#bdc3c7")
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:4px;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def amount_display(self, obj):
        return f"₹{obj.amount}"
    amount_display.short_description = "Amount"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        # Payment status cannot be changed directly via admin
        if obj and not request.user.is_superuser:
            return list(self.readonly_fields) + ["status", "amount_refunded"]
        return self.readonly_fields
