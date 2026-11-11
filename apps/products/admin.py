"""Django Admin for the products app."""

import uuid
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse

from .models import Category, Product, ProductImage, Cart, CartItem, WishlistItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "image_thumbnail", "name", "slug", "is_active",
        "products_count_link", "updated_at",
    )
    list_display_links = ("image_thumbnail", "name")
    list_editable = ("is_active",)
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("category_preview", "created_at", "updated_at")
    actions = ["mark_active", "mark_inactive"]

    fieldsets = (
        ("General Information", {
            "fields": ("name", "slug", "is_active", "description"),
        }),
        ("Media & Visuals", {
            "fields": ("image", "category_preview"),
        }),
        ("Audit Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;object-fit:cover;border-radius:4px;" alt="{}" />',
                obj.image.url, obj.name,
            )
        return "—"
    image_thumbnail.short_description = "Image"

    def category_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; border-radius: 6px;" />',
                obj.image.url,
            )
        return "No image uploaded yet"
    category_preview.short_description = "Image Preview"

    def products_count_link(self, obj):
        count = obj.products.count()
        url = reverse("admin:products_product_changelist") + f"?category__id__exact={obj.id}"
        return format_html(
            '<a href="{}" style="font-weight:600;">{} Products ↗</a>',
            url, count,
        )
    products_count_link.short_description = "Catalog Items"

    def mark_active(self, request, queryset):
        rows = queryset.update(is_active=True)
        self.message_user(request, f"{rows} categories marked as active.")
    mark_active.short_description = "Mark selected categories as Active"

    def mark_inactive(self, request, queryset):
        rows = queryset.update(is_active=False)
        self.message_user(request, f"{rows} categories marked as inactive.")
    mark_inactive.short_description = "Mark selected categories as Inactive"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "image_preview", "alt_text", "is_primary", "sort_order")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" class="ln-thumb-preview" alt="{}" />',
                obj.image.url, obj.alt_text or "Preview",
            )
        return "—"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "image_thumbnail", "name", "sku", "category", "subcategory_display",
        "price_display", "stock_badge", "status_badge", "is_featured", "updated_at",
    )
    list_display_links = ("image_thumbnail", "name")
    list_editable = ("is_featured",)
    list_filter = ("status", "category", "is_featured", "created_at")
    search_fields = ("name", "sku", "subcategory", "tags", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "image_large_preview", "discount_display", "created_at", "updated_at")
    inlines = [ProductImageInline]

    fieldsets = (
        ("🌿 Core Information", {
            "fields": ("name", ("category", "subcategory"), ("status", "is_featured")),
            "description": "Essential details to identify and classify the handcrafted product.",
        }),
        ("🏷️ SKU & Identifiers", {
            "fields": ("sku", "slug", "id"),
            "description": "Leave SKU blank to automatically generate a unique artisan SKU (e.g., LN-CAN-8F3B1A).",
        }),
        ("💰 Pricing & Inventory", {
            "fields": (
                ("price", "compare_at_price", "discount_display"),
                ("stock", "weight"),
            ),
            "description": "Base price (₹), optional compare-at original price (for sale discounts), inventory count, and weight in grams.",
        }),
        ("📸 Visual Preview", {
            "fields": ("image_large_preview",),
        }),
        ("📝 Artisan Story & Descriptions", {
            "fields": ("short_description", "description", "tags"),
            "description": "Short summary for store cards, full artisan description, and comma-separated search tags.",
        }),
        ("📦 Crafting, Care & Custom Specs", {
            "fields": ("care_instructions", "shipping_info", "details"),
            "description": 'Custom specs dictionary, e.g. {"Burn Time": "45-50 hrs", "Wax": "100% Soy Wax", "Scent Notes": "Lavender & Vanilla"}.',
        }),
        ("⏱️ Audit & Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = [
        "mark_as_active",
        "mark_as_draft",
        "mark_as_discontinued",
        "duplicate_products",
        "restock_ten_units",
    ]

    def image_thumbnail(self, obj):
        img = obj.primary_image
        if img and img.image:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;object-fit:cover;border-radius:4px;" alt="{}" />',
                img.image.url, obj.name,
            )
        return "—"
    image_thumbnail.short_description = "Visual"

    def image_large_preview(self, obj):
        img = obj.primary_image
        if img and img.image:
            return format_html(
                '<div style="display:flex; align-items:center; gap:16px;">'
                '<img src="{}" style="max-width: 140px; max-height: 140px; border-radius: 6px;" />'
                '<div><strong>Primary Image:</strong> {}</div>'
                '</div>',
                img.image.url, img.alt_text or obj.name,
            )
        return "No primary image uploaded yet."
    image_large_preview.short_description = "Current Primary Image"

    def price_display(self, obj):
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            return format_html(
                '<div><strong>₹{}</strong> <span style="text-decoration:line-through;color:#888;font-size:11px;">₹{}</span></div>',
                obj.price, obj.compare_at_price,
            )
        return format_html("<strong>₹{}</strong>", obj.price)
    price_display.short_description = "Price"
    price_display.admin_order_field = "price"

    def discount_display(self, obj):
        pct = obj.discount_percentage
        if pct:
            return format_html('<span style="color:#d97706;font-weight:600;">{}% OFF</span>', pct)
        return "No discount"
    discount_display.short_description = "Active Discount"

    def subcategory_display(self, obj):
        return obj.subcategory or "—"
    subcategory_display.short_description = "Subcategory"

    def stock_badge(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color:#dc2626;font-weight:600;">Out of Stock</span>')
        elif obj.stock <= 5:
            return format_html('<span style="color:#d97706;font-weight:600;">Low ({})</span>', obj.stock)
        return format_html('<span style="color:#16a34a;font-weight:600;">{} in stock</span>', obj.stock)
    stock_badge.short_description = "Inventory"
    stock_badge.admin_order_field = "stock"

    def status_badge(self, obj):
        if obj.status == Product.Status.ACTIVE:
            return format_html('<span style="color:#16a34a;font-weight:600;">Active</span>')
        elif obj.status == Product.Status.DRAFT:
            return format_html('<span style="color:#64748b;font-weight:600;">Draft</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;">Discontinued</span>')
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def mark_as_active(self, request, queryset):
        rows = queryset.update(status=Product.Status.ACTIVE)
        self.message_user(request, f"{rows} products marked as Active.", messages.SUCCESS)
    mark_as_active.short_description = "Mark selected products as Active"

    def mark_as_draft(self, request, queryset):
        rows = queryset.update(status=Product.Status.DRAFT)
        self.message_user(request, f"{rows} products marked as Draft.", messages.INFO)
    mark_as_draft.short_description = "Mark selected products as Draft"

    def mark_as_discontinued(self, request, queryset):
        rows = queryset.update(status=Product.Status.DISCONTINUED)
        self.message_user(request, f"{rows} products marked as Discontinued.", messages.WARNING)
    mark_as_discontinued.short_description = "Mark selected products as Discontinued"

    def restock_ten_units(self, request, queryset):
        for prod in queryset:
            prod.stock += 10
            prod.save(update_fields=["stock", "updated_at"])
        self.message_user(request, f"Added 10 units of stock to {queryset.count()} products.", messages.SUCCESS)
    restock_ten_units.short_description = "Quick Restock (+10 units)"

    def duplicate_products(self, request, queryset):
        count = 0
        for item in queryset:
            rand_suffix = uuid.uuid4().hex[:6].upper()
            cat_code = (item.category.slug[:3] if item.category and item.category.slug else "LAV").upper()
            new_item = Product.objects.create(
                name=f"{item.name} (Copy)",
                category=item.category,
                subcategory=item.subcategory,
                description=item.description,
                short_description=item.short_description,
                care_instructions=item.care_instructions,
                shipping_info=item.shipping_info,
                details=item.details,
                sku=f"LN-{cat_code}-{rand_suffix}",
                price=item.price,
                compare_at_price=item.compare_at_price,
                stock=item.stock,
                weight=item.weight,
                status=Product.Status.DRAFT,
                is_featured=False,
                tags=item.tags,
            )
            # Copy images
            for img in item.images.all():
                ProductImage.objects.create(
                    product=new_item,
                    image=img.image,
                    alt_text=img.alt_text,
                    is_primary=img.is_primary,
                    sort_order=img.sort_order,
                )
            count += 1
        self.message_user(request, f"Successfully duplicated {count} product(s) as Drafts.", messages.SUCCESS)
    duplicate_products.short_description = "Duplicate selected products (create Draft copy)"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product", "quantity", "unit_price_display", "line_total_display", "added_at")
    readonly_fields = ("product", "quantity", "unit_price_display", "line_total_display", "added_at")
    can_delete = True

    def unit_price_display(self, obj):
        return f"₹{obj.product.price}"
    unit_price_display.short_description = "Unit Price"

    def line_total_display(self, obj):
        return f"₹{obj.line_total}"
    line_total_display.short_description = "Line Total"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_identifier", "customer_email", "total_items", "subtotal_display", "updated_at")
    search_fields = ("customer__user__email", "session_key")
    readonly_fields = ("id", "session_key", "customer", "created_at", "updated_at")
    inlines = [CartItemInline]

    def cart_identifier(self, obj):
        if obj.customer:
            return f"Cart #{str(obj.id)[:8]} ({obj.customer.user.email})"
        return f"Guest Cart #{str(obj.id)[:8]} ({obj.session_key[:8]}...)"
    cart_identifier.short_description = "Cart ID"

    def customer_email(self, obj):
        return obj.customer.user.email if obj.customer else "Guest"
    customer_email.short_description = "Owner"

    def subtotal_display(self, obj):
        return f"₹{obj.subtotal}"
    subtotal_display.short_description = "Subtotal"


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("customer__user__email", "product__name", "product__sku")
    readonly_fields = ("created_at",)

