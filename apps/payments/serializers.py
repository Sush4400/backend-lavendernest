"""Serializers for the payments app."""

from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id", "order", "order_number", "provider",
            "razorpay_order_id", "razorpay_payment_id",
            "amount", "currency", "amount_refunded", "status",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "razorpay_order_id", "razorpay_payment_id",
            "amount", "status", "created_at", "updated_at",
        )


class CreatePaymentSerializer(serializers.Serializer):
    """Initiate payment for an order."""
    order_id = serializers.UUIDField()


class VerifyPaymentSerializer(serializers.Serializer):
    """Verify Razorpay payment after successful payment."""
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=128)
