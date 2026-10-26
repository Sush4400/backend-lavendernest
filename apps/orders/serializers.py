"""Serializers for the orders app."""

from rest_framework import serializers
from apps.users.serializers import AddressSerializer
from apps.products.serializers import ProductListSerializer
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id", "product", "product_name", "product_sku",
            "unit_price", "quantity", "line_total",
        )

    def get_line_total(self, obj):
        return str(obj.line_total)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source="customer.user.email", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "customer_email", "status", "payment_status",
            "shipping_full_name", "shipping_phone",
            "shipping_address_line1", "shipping_address_line2",
            "shipping_city", "shipping_state", "shipping_postal_code", "shipping_country",
            "subtotal", "shipping_cost", "discount_amount", "tax_amount", "total_amount",
            "tracking_number", "notes", "items", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "order_number", "status", "payment_status",
            "subtotal", "shipping_cost", "tax_amount", "total_amount",
            "created_at", "updated_at",
        )


class PlaceOrderSerializer(serializers.Serializer):
    """Serializer for placing an order from cart."""

    address_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_address_id(self, value):
        request = self.context["request"]
        customer = request.user.customer_profile
        from apps.users.models import Address
        if not Address.objects.filter(id=value, customer=customer).exists():
            raise serializers.ValidationError("Shipping address not found.")
        return value


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for staff to update order status."""

    class Meta:
        model = Order
        fields = ("status", "tracking_number", "notes")

    def validate_status(self, value):
        order = self.instance
        allowed_transitions = {
            Order.Status.PENDING: [Order.Status.CONFIRMED, Order.Status.CANCELLED],
            Order.Status.CONFIRMED: [Order.Status.PROCESSING, Order.Status.CANCELLED],
            Order.Status.PROCESSING: [Order.Status.SHIPPED, Order.Status.CANCELLED],
            Order.Status.SHIPPED: [Order.Status.DELIVERED],
            Order.Status.DELIVERED: [Order.Status.REFUNDED],
            Order.Status.CANCELLED: [],
            Order.Status.REFUNDED: [],
        }
        if order and value not in allowed_transitions.get(order.status, []):
            raise serializers.ValidationError(
                f"Cannot transition from '{order.get_status_display()}' to '{value}'."
            )
        return value
