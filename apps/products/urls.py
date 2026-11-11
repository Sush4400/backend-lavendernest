"""URL routing for the products app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")
router.register(r"", views.ProductViewSet, basename="product")

app_name = "products"

urlpatterns = [
    # Cart endpoints
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemView.as_view(), name="cart_items"),
    path("cart/items/<int:item_id>/", views.CartItemView.as_view(), name="cart_item_detail"),
    path("cart/clear/", views.CartItemView.as_view(), name="cart_clear"),
    path("wishlist/", views.WishlistViewSet.as_view({"get": "list", "post": "create"}), name="wishlist"),
    path(
        "wishlist/<int:pk>/",
        views.WishlistViewSet.as_view({"delete": "destroy"}),
        name="wishlist_detail",
    ),

    # Product/Category router
    path("", include(router.urls)),
]
