"""Views for the products app."""

import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, ProductImage, Cart, CartItem
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    CartSerializer,
    CartItemSerializer,
    CartQuantitySerializer,
    WishlistItemSerializer,
)
from .filters import ProductFilter
from .services import get_cart_for_request
from .models import WishlistItem
from apps.users.permissions import IsStaffOrAdmin

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD for product categories."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsStaffOrAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "retrieve") and not self._is_staff():
            qs = qs.filter(is_active=True)
        if self.action == "list":
            qs = qs.annotate(
                active_product_count=Count(
                    "products",
                    filter=Q(products__status=Product.Status.ACTIVE),
                )
            ).order_by("name")
        return qs

    def _is_staff(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role in ("staff", "admin")
        )


class ProductViewSet(viewsets.ModelViewSet):
    """Full CRUD for products with filtering, search, and ordering."""

    filterset_class = ProductFilter
    search_fields = ["name", "description", "sku", "tags"]
    ordering_fields = ["price", "created_at", "name", "stock"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Product.objects.select_related("category").prefetch_related("images")
        if self.action in ("list", "retrieve") and not self._is_staff():
            qs = qs.filter(status=Product.Status.ACTIVE)
        return qs

    def _is_staff(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role in ("staff", "admin")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    def get_object(self):
        """Accept both the product slug used by the storefront and the UUID API key."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        obj = queryset.filter(slug=lookup_value).first()
        if obj is None:
            obj = get_object_or_404(queryset, pk=lookup_value)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsStaffOrAdmin()]

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Return featured products."""
        products = self.get_queryset().filter(is_featured=True, status=Product.Status.ACTIVE)[:8]
        serializer = ProductListSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def upload_image(self, request, pk=None):
        """Upload an image for a product."""
        product = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)

        is_primary = not product.images.filter(is_primary=True).exists()
        product_image = ProductImage.objects.create(
            product=product,
            image=image_file,
            alt_text=request.data.get("alt_text", ""),
            is_primary=is_primary,
        )
        return Response(
            ProductImageSerializer(product_image).data,
            status=status.HTTP_201_CREATED,
        )


class CartView(generics.RetrieveAPIView):
    """Retrieve the current customer's or browser session's cart."""

    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        cart = get_cart_for_request(self.request)
        return Cart.objects.prefetch_related("items__product__images").get(pk=cart.pk)


class CartItemView(generics.GenericAPIView):
    """Add, update quantity, or remove items from the current cart."""

    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_cart(self):
        return get_cart_for_request(self.request)

    def post(self, request):
        """Add a product to cart or update quantity if already present."""
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            cart = self.get_cart()
            cart = Cart.objects.select_for_update().get(pk=cart.pk)
            product_id = serializer.validated_data["product_id"]
            quantity = serializer.validated_data.get("quantity", 1)
            try:
                product = Product.objects.select_for_update().get(
                    id=product_id, status=Product.Status.ACTIVE
                )
            except Product.DoesNotExist:
                return Response(
                    {"error": "Product not found or unavailable."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if quantity > product.stock:
                return Response(
                    {"error": f"Only {product.stock} unit(s) available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, product=product, defaults={"quantity": quantity}
            )
            if not created:
                new_qty = cart_item.quantity + quantity
                if new_qty > product.stock:
                    return Response(
                        {"error": f"Only {product.stock} unit(s) available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                cart_item.quantity = new_qty
                cart_item.save()

        return Response(
            CartItemSerializer(cart_item, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def patch(self, request, item_id):
        """Update quantity of a specific cart item."""
        cart = self.get_cart()
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            Cart.objects.select_for_update().get(pk=cart.pk)
            try:
                cart_item = CartItem.objects.select_for_update().select_related("product").get(
                    id=item_id, cart=cart
                )
            except CartItem.DoesNotExist:
                return Response({"error": "Item not in cart."}, status=status.HTTP_404_NOT_FOUND)
            if quantity > cart_item.product.stock:
                return Response(
                    {"error": f"Only {cart_item.product.stock} unit(s) available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart_item.quantity = quantity
            cart_item.save()

        return Response(CartItemSerializer(cart_item, context={"request": request}).data)

    def delete(self, request, item_id=None):
        """Remove an item from the cart."""
        cart = self.get_cart()
        if item_id is None:
            with transaction.atomic():
                Cart.objects.select_for_update().get(pk=cart.pk)
                cart.items.all().delete()
            return Response({"message": "Cart cleared."})
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not in cart."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            Cart.objects.select_for_update().get(pk=cart.pk)
            cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class WishlistViewSet(viewsets.ModelViewSet):
    """List, add, and remove products from the authenticated customer's wishlist."""

    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return WishlistItem.objects.filter(
            customer__user=self.request.user,
            product__status=Product.Status.ACTIVE,
        ).select_related("product", "product__category").prefetch_related("product__images")
