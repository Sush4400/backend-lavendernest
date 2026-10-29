"""Serializers for the orders app."""

from rest_framework import serializers
from apps.users.models import Address
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
            "shipping_method", "payment_method", "coupon_code",
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

    address_id = serializers.IntegerField(required=False, allow_null=True)
    shipping_address = serializers.DictField(required=False)
    save_address = serializers.BooleanField(required=False, default=False)
    shipping_method = serializers.ChoiceField(
        choices=Order.ShippingMethod.choices,
        required=False,
        default=Order.ShippingMethod.STANDARD,
    )
    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        required=False,
        default=Order.PaymentMethod.RAZORPAY,
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=30)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_shipping_address(self, value):
        required = (
            "full_name", "phone_number", "address_line1", "city",
            "state", "postal_code",
        )
        missing = [field for field in required if not value.get(field)]
        if missing:
            raise serializers.ValidationError(
                {field: "This field is required." for field in missing}
            )
        address_fields = set(required) | {"address_line2", "country"}
        values = {key: value[key] for key in address_fields if key in value}
        field_serializer = CheckoutAddressSerializer(data=values)
        field_serializer.is_valid(raise_exception=True)
        return field_serializer.validated_data

    def validate_address_id(self, value):
        request = self.context["request"]
        if value is None:
            return value
        if not Address.objects.filter(id=value, customer__user=request.user).exists():
            raise serializers.ValidationError("Shipping address not found.")
        return value

    def validate(self, attrs):
        address_id = attrs.get("address_id")
        shipping_address = attrs.get("shipping_address")
        has_address_id = address_id is not None
        has_shipping_address = bool(shipping_address)
        if has_address_id == has_shipping_address:
            raise serializers.ValidationError(
                "Provide exactly one of address_id or shipping_address."
            )
        if attrs.get("save_address") and not has_shipping_address:
            raise serializers.ValidationError(
                {"save_address": "Only a new shipping address can be saved."}
            )
        return attrs


class CheckoutSummarySerializer(serializers.Serializer):
    shipping_method = serializers.ChoiceField(
        choices=Order.ShippingMethod.choices,
        required=False,
        default=Order.ShippingMethod.STANDARD,
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=30)


class CheckoutAddressSerializer(serializers.Serializer):
    """Validated shipping address supplied directly during checkout."""

    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.RegexField(r"^\+?\d{9,15}$", max_length=17)
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=10)
    country = serializers.CharField(max_length=100, required=False, default="India")


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
