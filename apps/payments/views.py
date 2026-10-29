"""Views for the payments app."""

import json
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.users.models import Customer
from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentSerializer, VerifyPaymentSerializer
from .services import (
    PaymentGatewayError,
    create_razorpay_order,
    capture_payment,
    process_webhook,
)
from apps.users.permissions import IsCustomer

logger = logging.getLogger(__name__)


class CreatePaymentView(APIView):
    """Initiate a Razorpay payment order."""

    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer, _ = Customer.objects.get_or_create(user=request.user)
        try:
            order = Order.objects.get(
                id=serializer.validated_data["order_id"],
                customer=customer,
                payment_status=Order.PaymentStatus.PENDING,
                status__in=(Order.Status.PENDING, Order.Status.CONFIRMED),
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found or already paid."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.payment_method == Order.PaymentMethod.COD:
            return Response(
                {"error": "Cash on delivery orders do not need an online payment session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            razorpay_order = create_razorpay_order(order)
        except ValueError as e:
            logger.warning("Payment gateway is unavailable: %s", e)
            return Response(
                {"error": "Online payment is not configured. Please contact the store."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error("Razorpay order creation failed: %s", e)
            return Response(
                {"error": "Payment gateway error. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "order_number": order.order_number,
        })


class VerifyPaymentView(APIView):
    """Verify Razorpay payment after successful checkout."""

    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer, _ = Customer.objects.get_or_create(user=request.user)
        if not Payment.objects.filter(
            razorpay_order_id=serializer.validated_data["razorpay_order_id"],
            order__customer=customer,
        ).exists():
            return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment = capture_payment(
                razorpay_order_id=serializer.validated_data["razorpay_order_id"],
                razorpay_payment_id=serializer.validated_data["razorpay_payment_id"],
                razorpay_signature=serializer.validated_data["razorpay_signature"],
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentGatewayError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(PaymentSerializer(payment).data)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    """Handle Razorpay webhook events."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        razorpay_signature = request.headers.get("X-Razorpay-Signature", "")

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            process_webhook(
                payload,
                razorpay_signature,
                raw_body=request.body.decode("utf-8"),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "ok"})


class PaymentDetailView(APIView):
    """Retrieve payment details for an order."""

    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get(self, request, order_id):
        try:
            payment = Payment.objects.get(
                order__id=order_id,
                order__customer__user=request.user,
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)
