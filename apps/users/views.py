"""Views for the users app."""

import logging
from django.db import transaction
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.products.models import Cart
from apps.products.services import merge_guest_cart

from .models import User, Customer, Address, NewsletterSubscriber
from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    CustomerSerializer,
    AddressSerializer,
    ChangePasswordSerializer,
    NewsletterSubscriptionSerializer,
    ContactMessageSerializer,
)
from .permissions import IsCustomer, IsStaffOrAdmin

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        customer, _ = Customer.objects.get_or_create(user=user)
        session_key = request.session.session_key
        if session_key:
            cart, _ = Cart.objects.get_or_create(customer=customer)
            merge_guest_cart(cart, session_key)
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        logger.info("New user registered: %s", user.email)
        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT login view with extra user data."""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            user = User.objects.filter(email__iexact=request.data.get("email", "")).first()
            if user:
                customer, _ = Customer.objects.get_or_create(user=user)
                session_key = request.session.session_key
                if session_key:
                    cart, _ = Cart.objects.get_or_create(customer=customer)
                    merge_guest_cart(cart, session_key)
        return response


class LogoutView(APIView):
    """Blacklist the refresh token on logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("User logged out: %s", request.user.email)
            return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        except (KeyError, TokenError, TypeError, ValueError) as exc:
            logger.warning("Logout failed: %s", exc)
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve and update the authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {
                    "error": "Incorrect current password.",
                    "detail": "Incorrect current password.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        logger.info("Password changed for user: %s", user.email)

        # Generate fresh JWT tokens so the active session stays in sync
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Password updated successfully.",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve and update the customer's extended profile."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_object(self):
        customer, _ = Customer.objects.get_or_create(user=self.request.user)
        return customer


class AddressListCreateView(generics.ListCreateAPIView):
    """List and create addresses for the authenticated customer."""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Address.objects.filter(customer__user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific address."""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Address.objects.filter(customer__user=self.request.user)


class NewsletterSubscriptionView(APIView):
    """Subscribe an email address to the LavenderNest newsletter."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = NewsletterSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        with transaction.atomic():
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email, defaults={"is_active": True}
            )
            if not subscriber.is_active:
                subscriber.is_active = True
                subscriber.save(update_fields=["is_active"])
            customer = Customer.objects.filter(user__email__iexact=email).first()
            if customer and not customer.newsletter_subscribed:
                customer.newsletter_subscribed = True
                customer.save(update_fields=["newsletter_subscribed", "updated_at"])
        return Response(
            {"message": "Thanks for subscribing.", "subscribed": True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ContactMessageCreateView(generics.CreateAPIView):
    """Accept customer questions and special requests."""

    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]


class AdminCustomerListView(APIView):
    """Staff-only list of customers with order counts and spent totals."""

    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]

    def get(self, request):
        customers = Customer.objects.select_related("user").prefetch_related("orders").all().order_by("-created_at")
        results = []
        for c in customers:
            all_orders = c.orders.all()
            paid_sum = sum(o.total_amount for o in all_orders if o.payment_status == "paid")
            results.append({
                "id": str(c.id),
                "user_id": str(c.user.id),
                "email": c.user.email,
                "first_name": c.user.first_name,
                "last_name": c.user.last_name,
                "phone_number": c.phone_number,
                "role": c.user.role,
                "is_staff": c.user.is_staff,
                "date_joined": c.user.date_joined,
                "orders_count": all_orders.count(),
                "total_spent": float(paid_sum),
                "newsletter_subscribed": c.newsletter_subscribed,
            })
        return Response(results)
