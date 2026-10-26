"""Django Admin configuration for the users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Customer, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin panel configuration for the custom User model."""

    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "updated_at")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Roles & Permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )

    # Disable direct status changes by non-superusers
    def get_readonly_fields(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return self.readonly_fields + ("role", "is_superuser", "is_staff")
        return self.readonly_fields


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin panel for customer profiles."""

    list_display = ("user", "phone_number", "newsletter_subscribed", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone_number")
    list_filter = ("newsletter_subscribed",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [AddressInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin panel for addresses."""

    list_display = ("full_name", "city", "state", "country", "is_default", "address_type")
    search_fields = ("full_name", "city", "state", "customer__user__email")
    list_filter = ("address_type", "is_default", "country", "state")
    readonly_fields = ("created_at", "updated_at")
