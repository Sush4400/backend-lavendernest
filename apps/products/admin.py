"""Django Admin for the products app."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, Cart, CartItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "product_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    def product_count(self, obj):
        return obj.products.filter(status=Product.Status.ACTIVE).count()
    product_count.short_description = "Active Products"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "sort_order", "image_preview")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="60" />', obj.image.url)
        return "—"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "sku", "category", "price", "stock", "status",
        "is_featured", "updated_at",
    )
    list_filter = ("status", "category", "is_featured")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable = ("status", "is_featured", "price")
    inlines = [ProductImageInline]
    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "name", "slug", "sku", "category", "status", "is_featured"),
        }),
        ("Pricing & Inventory", {
            "fields": ("price", "compare_at_price", "stock", "weight"),
        }),
        ("Content", {
            "fields": ("short_description", "description", "tags"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    actions = ["mark_as_active", "mark_as_draft", "mark_as_discontinued"]

    def mark_as_active(self, request, queryset):
        queryset.update(status=Product.Status.ACTIVE)
    mark_as_active.short_description = "Mark selected products as Active"

    def mark_as_draft(self, request, queryset):
        queryset.update(status=Product.Status.DRAFT)
    mark_as_draft.short_description = "Mark selected products as Draft"

    def mark_as_discontinued(self, request, queryset):
        queryset.update(status=Product.Status.DISCONTINUED)
    mark_as_discontinued.short_description = "Mark as Discontinued"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("added_at", "line_total")

    def line_total(self, obj):
        return f"₹{obj.line_total}"
    line_total.short_description = "Line Total"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("__str__", "total_items", "subtotal_display", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CartItemInline]

    def subtotal_display(self, obj):
        return f"₹{obj.subtotal}"
    subtotal_display.short_description = "Subtotal"
