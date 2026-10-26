"""Serializers for inventory app."""

from rest_framework import serializers
from apps.products.models import Product
from .models import InventoryMovement


class InventoryMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InventoryMovement
        fields = (
            "id", "product", "product_name", "movement_type",
            "quantity_change", "stock_before", "stock_after",
            "reference", "created_at",
        )
        read_only_fields = ("id", "stock_before", "stock_after", "created_at")


class AddStockSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(required=False, allow_blank=True, default="")


class AdjustStockSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    new_quantity = serializers.IntegerField(min_value=0)
    reference = serializers.CharField(required=False, allow_blank=True, default="")


class LowStockProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "sku", "stock", "category_name", "status")
