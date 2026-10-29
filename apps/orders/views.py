"""Views for the orders app."""

import logging
from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order
from .serializers import (
    OrderSerializer,
    PlaceOrderSerializer,
    OrderStatusUpdateSerializer,
    CheckoutSummarySerializer,
)
from .services import (
    place_order,
    cancel_order,
    validate_cart_for_checkout,
    calculate_discount,
    calculate_shipping,
)
from apps.users.permissions import IsStaffOrAdmin
from apps.products.models import Cart
from apps.users.models import Customer

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.GenericViewSet):
    """Order management viewset."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.prefetch_related("items__product__images").select_related("customer__user")
        if user.role in ("staff", "admin"):
            return qs.all()
        return qs.filter(customer__user=user)

    def get_serializer_class(self):
        if self.action == "create":
            return PlaceOrderSerializer
        if self.action in ("update_status",):
            return OrderStatusUpdateSerializer
        return OrderSerializer

    def list(self, request):
        """List orders for the authenticated user (or all for staff)."""
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(OrderSerializer(page, many=True).data)
        return Response(OrderSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        """Retrieve a specific order."""
        try:
            order = self.get_queryset().get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)

    def create(self, request):
        """Place a new order from the customer's cart."""
        serializer = PlaceOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        customer, _ = Customer.objects.get_or_create(user=request.user)

        # Validate cart
        try:
            cart = Cart.objects.prefetch_related("items__product").get(customer=customer)
        except Cart.DoesNotExist:
            return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        errors = validate_cart_for_checkout(cart)
        if errors:
            return Response({"cart_errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = place_order(
                customer=customer,
                address_id=serializer.validated_data.get("address_id"),
                shipping_address=serializer.validated_data.get("shipping_address"),
                notes=serializer.validated_data.get("notes", ""),
                shipping_method=serializer.validated_data["shipping_method"],
                payment_method=serializer.validated_data["payment_method"],
                coupon_code=serializer.validated_data.get("coupon_code", ""),
                save_address=serializer.validated_data["save_address"],
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Customer or staff can cancel an unshipped order."""
        try:
            order = self.get_queryset().get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = cancel_order(order)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["patch"], permission_classes=[IsStaffOrAdmin])
    def update_status(self, request, pk=None):
        """Staff-only: Update order status and tracking."""
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("status") == Order.Status.CANCELLED:
            try:
                order = cancel_order(order)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            serializer.instance = order
        order = serializer.save()
        if (
            order.payment_method == Order.PaymentMethod.COD
            and order.status == Order.Status.DELIVERED
        ):
            from apps.payments.models import Payment
            payment = Payment.objects.filter(order=order, provider=Payment.Provider.COD).first()
            if payment:
                payment.status = Payment.Status.CAPTURED
                payment.save(update_fields=["status", "updated_at"])
                order.payment_status = Order.PaymentStatus.PAID
                order.save(update_fields=["payment_status", "updated_at"])
        logger.info("Order %s status updated to %s by %s", order.order_number, order.status, request.user.email)
        return Response(OrderSerializer(order).data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Return the authenticated customer's order history."""
        qs = self.get_queryset().order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(OrderSerializer(page, many=True).data)
        return Response(OrderSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """Return server-calculated checkout totals and validate a promotion."""
        serializer = CheckoutSummarySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer, _ = Customer.objects.get_or_create(user=request.user)
        cart = Cart.objects.filter(customer=customer).first()
        if not cart or not cart.items.exists():
            return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        errors = validate_cart_for_checkout(cart)
        if errors:
            return Response({"cart_errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(
            (item.product.price * item.quantity for item in cart.items.select_related("product")),
            Decimal("0.00"),
        )
        try:
            discount = calculate_discount(subtotal, serializer.validated_data.get("coupon_code", ""))
        except ValueError as exc:
            return Response({"coupon_code": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        shipping_method = serializer.validated_data["shipping_method"]
        shipping = calculate_shipping(subtotal, shipping_method)
        total = max(Decimal("0.00"), subtotal + shipping - discount)
        return Response({
            "subtotal": str(subtotal),
            "shipping_cost": str(shipping),
            "discount_amount": str(discount),
            "tax_amount": "0.00",
            "total_amount": str(total),
            "currency": "INR",
            "coupon_code": serializer.validated_data.get("coupon_code", "").strip().upper(),
        })

    @action(detail=False, methods=["get"])
    def track(self, request):
        """Return tracking details only to the order owner or staff."""
        order_number = request.query_params.get("order_number", "").strip()
        if not order_number:
            return Response(
                {"order_number": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order = self.get_queryset().get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)
