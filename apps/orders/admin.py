"""Django Admin for the orders app."""

from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
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
        "order_number", "customer_email", "status", "payment_status",
        "total_display", "created_at",
    )
    list_filter = ("status", "payment_status", "created_at", "shipping_country")
    search_fields = ("order_number", "customer__user__email", "shipping_full_name")
    readonly_fields = (
        "id", "order_number", "customer", "subtotal", "shipping_cost",
        "discount_amount", "tax_amount", "total_amount",
        "payment_status", "created_at", "updated_at",
    )
    inlines = [OrderItemInline]
    ordering = ["-created_at"]

    fieldsets = (
        ("Order Info", {
            "fields": ("id", "order_number", "customer", "status", "payment_status"),
        }),
        ("Shipping Address", {
            "fields": (
                "shipping_full_name", "shipping_phone",
                "shipping_address_line1", "shipping_address_line2",
                "shipping_city", "shipping_state", "shipping_postal_code", "shipping_country",
            ),
        }),
        ("Financials", {
            "fields": ("subtotal", "shipping_cost", "discount_amount", "tax_amount", "total_amount"),
        }),
        ("Tracking & Notes", {
            "fields": ("tracking_number", "notes"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def customer_email(self, obj):
        return obj.customer.user.email
    customer_email.short_description = "Customer"

    def total_display(self, obj):
        return format_html("<strong>₹{}</strong>", obj.total_amount)
    total_display.short_description = "Total"

    def get_readonly_fields(self, request, obj=None):
        # Prevent changing payment_status through admin
        base = list(self.readonly_fields)
        if obj and not request.user.is_superuser:
            base.append("status")
        return base

    def has_delete_permission(self, request, obj=None):
        # Preserve historical order data
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
