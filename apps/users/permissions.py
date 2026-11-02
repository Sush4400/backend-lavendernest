"""Custom permissions for the users app."""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import User


class IsCustomer(BasePermission):
    """Allow access only to users with customer role."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in (User.Role.CUSTOMER, User.Role.ADMIN)
        )


class IsAdminUser(BasePermission):
    """Allow access only to admin-role users."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.ADMIN
        )


class IsOwnerOrAdmin(BasePermission):
    """Allow object access only to the owner or admins."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        # Address ownership check
        if hasattr(obj, "customer"):
            return obj.customer.user == request.user
        # Order/Payment ownership check
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False


class IsStaffOrAdmin(BasePermission):
    """Allow access to staff or admin users."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (
                request.user.role in (User.Role.STAFF, User.Role.ADMIN)
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class ReadOnly(BasePermission):
    """Allow only read-only access."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
