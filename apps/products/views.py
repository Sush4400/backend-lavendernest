"""Views for the products app."""

import logging
from django.db import transaction
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
)
from .filters import ProductFilter
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
        if self.action in ("list",):
            qs = qs.filter(is_active=True)
        return qs


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
    """Retrieve the authenticated customer's cart."""

    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, _ = Cart.objects.prefetch_related(
            "items__product__images"
        ).get_or_create(customer=self.request.user.customer_profile)
        return cart


class CartItemView(generics.GenericAPIView):
    """Add, update quantity, or remove items from cart."""

    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self):
        cart, _ = Cart.objects.get_or_create(
            customer=self.request.user.customer_profile
        )
        return cart

    def post(self, request):
        """Add a product to cart or update quantity if already present."""
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart()
        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data.get("quantity", 1)

        with transaction.atomic():
            product = Product.objects.select_for_update().get(
                id=product_id, status=Product.Status.ACTIVE
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
        try:
            cart_item = CartItem.objects.select_for_update().get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not in cart."}, status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get("quantity")
        if not quantity or int(quantity) < 1:
            return Response({"error": "Quantity must be ≥ 1."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if int(quantity) > cart_item.product.stock:
                return Response(
                    {"error": f"Only {cart_item.product.stock} unit(s) available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart_item.quantity = int(quantity)
            cart_item.save()

        return Response(CartItemSerializer(cart_item, context={"request": request}).data)

    def delete(self, request, item_id):
        """Remove an item from the cart."""
        cart = self.get_cart()
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not in cart."}, status=status.HTTP_404_NOT_FOUND)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete_all(self, request):
        """Clear all items from cart."""
        cart = self.get_cart()
        cart.items.all().delete()
        return Response({"message": "Cart cleared."})
