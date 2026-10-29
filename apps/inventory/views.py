"""Views for the inventory app."""

import logging
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.products.models import Product
from apps.users.permissions import IsStaffOrAdmin
from .models import InventoryMovement
from .serializers import (
    InventoryMovementSerializer,
    AddStockSerializer,
    AdjustStockSerializer,
    LowStockProductSerializer,
)
from .services import add_stock, adjust_stock, get_low_stock_products

logger = logging.getLogger(__name__)


class InventoryMovementListView(generics.ListAPIView):
    """List all inventory movements (staff only)."""

    serializer_class = InventoryMovementSerializer
    permission_classes = [IsStaffOrAdmin]
    filterset_fields = ["product", "movement_type"]
    search_fields = ["product__name", "reference"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return InventoryMovement.objects.select_related("product").all()


class ProductInventoryMovementView(generics.ListAPIView):
    """List inventory movements for a specific product."""

    serializer_class = InventoryMovementSerializer
    permission_classes = [IsStaffOrAdmin]

    def get_queryset(self):
        return InventoryMovement.objects.filter(
            product_id=self.kwargs["product_id"]
        ).order_by("-created_at")


class AddStockView(APIView):
    """Add stock to a product."""

    permission_classes = [IsStaffOrAdmin]

    def post(self, request):
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.get(id=serializer.validated_data["product_id"])
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        movement = add_stock(
            product=product,
            quantity=serializer.validated_data["quantity"],
            reference=serializer.validated_data.get("reference", ""),
        )
        return Response(InventoryMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class AdjustStockView(APIView):
    """Manually adjust stock for a product."""

    permission_classes = [IsStaffOrAdmin]

    def post(self, request):
        serializer = AdjustStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.get(id=serializer.validated_data["product_id"])
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        movement = adjust_stock(
            product=product,
            new_quantity=serializer.validated_data["new_quantity"],
            reference=serializer.validated_data.get("reference", ""),
        )
        return Response(InventoryMovementSerializer(movement).data, status=status.HTTP_200_OK)


class LowStockView(generics.ListAPIView):
    """Return products with stock below the threshold."""

    serializer_class = LowStockProductSerializer
    permission_classes = [IsStaffOrAdmin]

    def get_queryset(self):
        try:
            threshold = int(self.request.query_params.get("threshold", 5))
        except ValueError as exc:
            raise ValidationError({"threshold": "Enter a whole number."}) from exc
        if threshold < 0:
            raise ValidationError({"threshold": "Ensure this value is greater than or equal to 0."})
        return get_low_stock_products(threshold)
