"""Django Admin for the products app."""

import uuid
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect

from .models import Category, Product, ProductImage, ProductGroup, Cart, CartItem, WishlistItem


class ProductGroupMembershipInline(admin.TabularInline):
    """Inline to assign and view products in a Product Group."""

    model = Product.groups.through
    extra = 1
    autocomplete_fields = ["product"]
    verbose_name = "Assigned Product"
    verbose_name_plural = "Assigned Products in this Group"


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    """Admin configuration for curated product groups / collections."""

    list_display = (
        "thumbnail_preview", "name", "slug", "badge_display",
        "products_count_link", "is_active", "sort_order", "updated_at",
    )
    list_display_links = ("thumbnail_preview", "name")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "description", "badge_text")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("thumbnail_preview", "created_at", "updated_at")
    inlines = [ProductGroupMembershipInline]
    actions = ["mark_active", "mark_inactive"]

    fieldsets = (
        ("Group Identity", {
            "fields": ("name", "slug", ("badge_text", "is_active", "sort_order")),
            "description": "Define the collection name, unique slug, and optional highlight badge.",
        }),
        ("Artisan Description & Media", {
            "fields": ("description", "image", "thumbnail_preview"),
        }),
        ("Audit Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:42px;height:42px;object-fit:cover;border-radius:6px;border:1px solid #d8bfe4;" alt="{}" />',
                obj.image.url, obj.name,
            )
        return format_html('<span style="color:#a897b5;font-size:11px;">No cover</span>')
    thumbnail_preview.short_description = "Cover"

    def badge_display(self, obj):
        if obj.badge_text:
            return format_html(
                '<span style="background:#f3e8f8;color:#7d4a8f;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;border:1px solid #dec3e9;">{}</span>',
                obj.badge_text,
            )
        return "—"
    badge_display.short_description = "Badge"

    def products_count_link(self, obj):
        count = obj.products.count()
        url = reverse("admin:products_product_changelist") + f"?groups__id__exact={obj.id}"
        return format_html(
            '<a href="{}" style="font-weight:600;color:#6b3582;">{} Products ↗</a>',
            url, count,
        )
    products_count_link.short_description = "Products in Group"

    def mark_active(self, request, queryset):
        rows = queryset.update(is_active=True)
        self.message_user(request, f"{rows} product groups marked as active.", messages.SUCCESS)
    mark_active.short_description = "Mark selected groups as Active"

    def mark_inactive(self, request, queryset):
        rows = queryset.update(is_active=False)
        self.message_user(request, f"{rows} product groups marked as inactive.", messages.INFO)
    mark_inactive.short_description = "Mark selected groups as Inactive"


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
                '<img src="{}" class="ln-thumb-preview" alt="{}" style="max-width:48px;max-height:48px;border-radius:4px;" />',
                obj.image.url, obj.alt_text or "Preview",
            )
        return "—"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "image_thumbnail", "name", "sku", "category", "groups_display",
        "price_display", "stock_badge", "status_badge", "is_featured", "updated_at",
    )
    list_display_links = ("image_thumbnail", "name")
    list_editable = ("is_featured",)
    list_filter = ("status", "category", "groups", "is_featured", "created_at")
    search_fields = ("name", "sku", "subcategory", "tags", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("groups",)
    readonly_fields = ("id", "image_large_preview", "discount_display", "created_at", "updated_at")
    inlines = [ProductImageInline]

    fieldsets = (
        ("🌿 Core Information", {
            "fields": ("name", ("category", "subcategory"), "groups", ("status", "is_featured")),
            "description": "Essential details to identify, categorize, and group the handcrafted product.",
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
        "assign_to_group",
        "remove_from_all_groups",
        "mark_as_active",
        "mark_as_draft",
        "mark_as_discontinued",
        "set_as_featured",
        "unset_as_featured",
        "duplicate_products",
        "restock_ten_units",
        "restock_fifty_units",
    ]

    def image_thumbnail(self, obj):
        img = obj.primary_image
        if img and img.image:
            return format_html(
                '<img src="{}" style="width:38px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #ebddee;" alt="{}" />',
                img.image.url, obj.name,
            )
        return "—"
    image_thumbnail.short_description = "Visual"

    def groups_display(self, obj):
        groups = obj.groups.all()
        if not groups:
            return "—"
        badges = [
            f'<span style="background:#f3e8f8;color:#7d4a8f;padding:2px 7px;border-radius:10px;font-size:10.5px;font-weight:600;margin-right:3px;display:inline-block;border:1px solid #dec3e9;">{g.name}</span>'
            for g in groups[:3]
        ]
        if groups.count() > 3:
            badges.append(f'<span style="color:#888;font-size:10px;">+{groups.count() - 3}</span>')
        return format_html("".join(badges))
    groups_display.short_description = "Assigned Groups"

    def image_large_preview(self, obj):
        img = obj.primary_image
        if img and img.image:
            return format_html(
                '<div style="display:flex; align-items:center; gap:16px;">'
                '<img src="{}" style="max-width: 140px; max-height: 140px; border-radius: 6px; border:1px solid #ebddee;" />'
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
            return format_html('<span style="color:#dc2626;font-weight:600;background:#fee2e2;padding:2px 7px;border-radius:4px;font-size:11px;">Out of Stock</span>')
        elif obj.stock <= 5:
            return format_html('<span style="color:#d97706;font-weight:600;background:#fef3c7;padding:2px 7px;border-radius:4px;font-size:11px;">Low ({})</span>', obj.stock)
        return format_html('<span style="color:#16a34a;font-weight:600;background:#dcfce7;padding:2px 7px;border-radius:4px;font-size:11px;">{} in stock</span>', obj.stock)
    stock_badge.short_description = "Inventory"
    stock_badge.admin_order_field = "stock"

    def status_badge(self, obj):
        if obj.status == Product.Status.ACTIVE:
            return format_html('<span style="color:#16a34a;font-weight:600;background:#dcfce7;padding:2px 7px;border-radius:4px;font-size:11px;">Active</span>')
        elif obj.status == Product.Status.DRAFT:
            return format_html('<span style="color:#64748b;font-weight:600;background:#f1f5f9;padding:2px 7px;border-radius:4px;font-size:11px;">Draft</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;background:#fee2e2;padding:2px 7px;border-radius:4px;font-size:11px;">Discontinued</span>')
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def assign_to_group(self, request, queryset):
        """Action allowing the admin to assign selected products to a group."""
        if "apply" in request.POST:
            group_id = request.POST.get("target_group")
            if not group_id:
                self.message_user(request, "Please select a target Product Group.", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
            try:
                group = ProductGroup.objects.get(id=group_id)
                group.products.add(*queryset)
                self.message_user(
                    request,
                    f"Successfully assigned {queryset.count()} product(s) to group '{group.name}'.",
                    level=messages.SUCCESS,
                )
            except ProductGroup.DoesNotExist:
                self.message_user(request, "Selected group does not exist.", level=messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())

        groups = ProductGroup.objects.filter(is_active=True).order_by("name")
        return render(
            request,
            "admin/products/assign_group.html",
            context={
                "products": queryset,
                "groups": groups,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )
    assign_to_group.short_description = "📦 Assign selected products to a Product Group"

    def remove_from_all_groups(self, request, queryset):
        for product in queryset:
            product.groups.clear()
        self.message_user(request, f"Removed group associations from {queryset.count()} product(s).", messages.INFO)
    remove_from_all_groups.short_description = "❌ Remove selected products from all Groups"

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

    def set_as_featured(self, request, queryset):
        rows = queryset.update(is_featured=True)
        self.message_user(request, f"{rows} products marked as Featured.", messages.SUCCESS)
    set_as_featured.short_description = "⭐ Set selected products as Featured"

    def unset_as_featured(self, request, queryset):
        rows = queryset.update(is_featured=False)
        self.message_user(request, f"{rows} products removed from Featured.", messages.INFO)
    unset_as_featured.short_description = "Remove selected products from Featured"

    def restock_ten_units(self, request, queryset):
        for prod in queryset:
            prod.stock += 10
            prod.save(update_fields=["stock", "updated_at"])
        self.message_user(request, f"Added 10 units of stock to {queryset.count()} products.", messages.SUCCESS)
    restock_ten_units.short_description = "Quick Restock (+10 units)"

    def restock_fifty_units(self, request, queryset):
        for prod in queryset:
            prod.stock += 50
            prod.save(update_fields=["stock", "updated_at"])
        self.message_user(request, f"Added 50 units of stock to {queryset.count()} products.", messages.SUCCESS)
    restock_fifty_units.short_description = "Bulk Restock (+50 units)"

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
            # Copy group memberships
            new_item.groups.set(item.groups.all())
            count += 1
        self.message_user(request, f"Successfully duplicated {count} product(s) as Drafts.", messages.SUCCESS)
    duplicate_products.short_description = "Duplicate selected products (create Draft copy)"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images", "groups")


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

