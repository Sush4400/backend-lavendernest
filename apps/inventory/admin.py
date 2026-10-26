"""Django Admin for the inventory app."""

from django.contrib import admin
from django.utils.html import format_html
from .models import InventoryMovement


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product", "movement_type_badge", "quantity_change_display",
        "stock_before", "stock_after", "reference", "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "product__sku", "reference")
    readonly_fields = (
        "product", "movement_type", "quantity_change",
        "stock_before", "stock_after", "reference", "created_at",
    )
    ordering = ["-created_at"]

    def movement_type_badge(self, obj):
        colors = {
            "addition": "#2ecc71",
            "deduction": "#e74c3c",
            "adjustment": "#f39c12",
            "return": "#3498db",
            "damage": "#8e44ad",
        }
        color = colors.get(obj.movement_type, "#bdc3c7")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;">{}</span>',
            color,
            obj.get_movement_type_display(),
        )
    movement_type_badge.short_description = "Type"

    def quantity_change_display(self, obj):
        color = "#2ecc71" if obj.quantity_change > 0 else "#e74c3c"
        sign = "+" if obj.quantity_change > 0 else ""
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}{}</span>',
            color, sign, obj.quantity_change,
        )
    quantity_change_display.short_description = "Change"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
