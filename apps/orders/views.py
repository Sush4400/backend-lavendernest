"""Views for the orders app."""

import logging
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer, PlaceOrderSerializer, OrderStatusUpdateSerializer
from .services import place_order, cancel_order, validate_cart_for_checkout
from apps.users.permissions import IsOwnerOrAdmin, IsStaffOrAdmin
from apps.products.models import Cart

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.GenericViewSet):
    """Order management viewset."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.prefetch_related("items__product__images").select_related("customer__user")
        if user.role in ("staff", "admin"):
            return qs.all()
        return qs.filter(customer=user.customer_profile)

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

        customer = request.user.customer_profile

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
                address_id=serializer.validated_data["address_id"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Customer or staff can cancel a pending/confirmed order."""
        try:
            order = self.get_queryset().get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = cancel_order(order, cancelled_by_user=(request.user.role == "customer"))
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
        serializer.save()
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
