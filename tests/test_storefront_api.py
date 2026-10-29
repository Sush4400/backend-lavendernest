"""End-to-end API coverage for the storefront's customer flows."""

from decimal import Decimal
import hashlib
import hmac
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.products.models import Cart, CartItem, Category, Product, WishlistItem
from apps.users.models import Address, ContactMessage, Customer, NewsletterSubscriber

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    user = User.objects.create_user(
        email="shopper@example.com",
        password="Lavender123!",
        first_name="Aarushi",
        last_name="Mehta",
    )
    return Customer.objects.get(user=user)


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Scented Candles", slug="candles")
    return Product.objects.create(
        name="Rose Bloom Candle",
        sku="ROSE-001",
        slug="rose-bloom-candle",
        category=category,
        price=Decimal("799.00"),
        compare_at_price=Decimal("999.00"),
        stock=10,
        status=Product.Status.ACTIVE,
        description="A handmade floral candle.",
        short_description="A softly scented rose candle.",
        subcategory="flower",
        details={"waxType": "Soy wax"},
        care_instructions="Trim the wick before lighting.",
        shipping_info="Ships in two business days.",
    )


@pytest.mark.django_db
class TestCatalogAndCart:
    def test_slug_detail_and_storefront_category_filter(self, api_client, product):
        response = api_client.get(f"/api/products/{product.slug}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(product.id)
        assert response.data["details"] == {"waxType": "Soy wax"}

        response = api_client.get("/api/products/?category__slug=candles&subcategory=flower")
        assert response.status_code == status.HTTP_200_OK
        assert [row["id"] for row in response.data["results"]] == [str(product.id)]

    def test_guest_cart_can_be_created_updated_and_cleared(self, api_client, product):
        response = api_client.get("/api/products/cart/")
        assert response.status_code == status.HTTP_200_OK

        response = api_client.post(
            "/api/products/cart/items/",
            {"product_id": str(product.id), "quantity": 2},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        item_id = response.data["id"]

        response = api_client.patch(
            f"/api/products/cart/items/{item_id}/",
            {"quantity": 3},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["quantity"] == 3

        response = api_client.delete("/api/products/cart/clear/")
        assert response.status_code == status.HTTP_200_OK
        assert CartItem.objects.count() == 0

    def test_cart_rejects_quantity_above_stock(self, api_client, product):
        product.stock = 1
        product.save(update_fields=["stock"])
        api_client.get("/api/products/cart/")

        response = api_client.post(
            "/api/products/cart/items/",
            {"product_id": str(product.id), "quantity": 2},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wishlist_is_customer_scoped(self, api_client, customer, product):
        api_client.force_authenticate(user=customer.user)
        response = api_client.post(
            "/api/products/wishlist/",
            {"product_id": str(product.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        item_id = response.data["id"]
        assert WishlistItem.objects.filter(customer=customer, product=product).exists()

        response = api_client.get("/api/products/wishlist/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["product"]["name"] == product.name

        other = User.objects.create_user(email="other@example.com", password="Lavender123!")
        api_client.force_authenticate(user=other)
        response = api_client.delete(f"/api/products/wishlist/{item_id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert WishlistItem.objects.filter(pk=item_id).exists()


@pytest.mark.django_db
class TestCheckoutAndOrders:
    def test_guest_cannot_create_orders(self, api_client):
        response = api_client.post("/api/orders/", {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_checkout_summary_and_cod_order(self, api_client, customer, product):
        cart = Cart.objects.create(customer=customer)
        CartItem.objects.create(cart=cart, product=product, quantity=2)
        api_client.force_authenticate(user=customer.user)

        response = api_client.post(
            "/api/orders/checkout/",
            {"shipping_method": "express", "coupon_code": "NEST10"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["subtotal"] == "1598.00"
        assert response.data["shipping_cost"] == "120.00"
        assert response.data["discount_amount"] == "159.80"
        assert response.data["total_amount"] == "1558.20"

        response = api_client.post(
            "/api/orders/",
            {
                "shipping_address": {
                    "full_name": "Aarushi Mehta",
                    "phone_number": "+919876543210",
                    "address_line1": "123 Green Park",
                    "address_line2": "Apt 4B",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "postal_code": "560001",
                    "country": "India",
                },
                "shipping_method": "express",
                "payment_method": "cod",
                "coupon_code": "NEST10",
                "save_address": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.get(pk=response.data["id"])
        assert order.status == Order.Status.CONFIRMED
        assert order.payment_status == Order.PaymentStatus.PENDING
        assert order.shipping_full_name == "Aarushi Mehta"
        assert order.total_amount == Decimal("1558.20")
        assert order.payment_method == Order.PaymentMethod.COD
        assert order.items.get().unit_price == Decimal("799.00")
        assert product.__class__.objects.get(pk=product.pk).stock == 8
        assert not CartItem.objects.filter(cart=cart).exists()
        assert Address.objects.filter(customer=customer).count() == 1
        assert Payment.objects.get(order=order).provider == Payment.Provider.COD

    def test_bad_coupon_does_not_create_order_or_consume_stock(
        self, api_client, customer, product
    ):
        cart = Cart.objects.create(customer=customer)
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        api_client.force_authenticate(user=customer.user)

        response = api_client.post(
            "/api/orders/",
            {
                "shipping_address": {
                    "full_name": "Aarushi Mehta",
                    "phone_number": "+919876543210",
                    "address_line1": "123 Green Park",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "postal_code": "560001",
                },
                "coupon_code": "NOT-A-COUPON",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Order.objects.count() == 0
        assert Product.objects.get(pk=product.pk).stock == 10
        assert CartItem.objects.filter(cart=cart).exists()

    def test_cancelling_order_restores_inventory_once(self, api_client, customer, product):
        cart = Cart.objects.create(customer=customer)
        CartItem.objects.create(cart=cart, product=product, quantity=2)
        api_client.force_authenticate(user=customer.user)
        response = api_client.post(
            "/api/orders/",
            {
                "shipping_address": {
                    "full_name": "Aarushi Mehta",
                    "phone_number": "+919876543210",
                    "address_line1": "123 Green Park",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "postal_code": "560001",
                },
                "payment_method": "cod",
            },
            format="json",
        )
        order_id = response.data["id"]
        assert Product.objects.get(pk=product.pk).stock == 8

        response = api_client.post(f"/api/orders/{order_id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert Product.objects.get(pk=product.pk).stock == 10

        response = api_client.post(f"/api/orders/{order_id}/cancel/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Product.objects.get(pk=product.pk).stock == 10

    def test_orders_and_tracking_are_private(self, api_client, customer, product):
        order = Order.objects.create(
            customer=customer,
            shipping_full_name="Aarushi Mehta",
            shipping_phone="+919876543210",
            shipping_address_line1="123 Green Park",
            shipping_city="Bangalore",
            shipping_state="Karnataka",
            shipping_postal_code="560001",
            subtotal=product.price,
            total_amount=product.price,
        )
        other = User.objects.create_user(email="other@example.com", password="Lavender123!")
        api_client.force_authenticate(user=other)
        response = api_client.get(f"/api/orders/{order.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = api_client.get(
            "/api/orders/track/", {"order_number": order.order_number}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestStorefrontForms:
    def test_newsletter_subscription_is_idempotent(self, api_client, customer):
        first = api_client.post(
            "/api/auth/newsletter/subscribe/",
            {"email": customer.user.email.upper()},
            format="json",
        )
        second = api_client.post(
            "/api/auth/newsletter/subscribe/",
            {"email": customer.user.email},
            format="json",
        )
        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_200_OK
        assert NewsletterSubscriber.objects.count() == 1
        customer.refresh_from_db()
        assert customer.newsletter_subscribed

    def test_contact_form_validates_and_stores_messages(self, api_client):
        response = api_client.post(
            "/api/auth/contact/",
            {
                "name": "Aarushi",
                "email": "aarushi@example.com",
                "topic": "Order help",
                "message": "Could you help me track my parcel?",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert ContactMessage.objects.count() == 1


@pytest.mark.django_db
class TestPayments:
    def test_online_payment_is_verified_and_captured(
        self, api_client, customer, monkeypatch
    ):
        order = Order.objects.create(
            customer=customer,
            shipping_full_name="Aarushi Mehta",
            shipping_phone="+919876543210",
            shipping_address_line1="123 Green Park",
            shipping_city="Bangalore",
            shipping_state="Karnataka",
            shipping_postal_code="560001",
            subtotal=Decimal("799.00"),
            shipping_cost=Decimal("70.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("869.00"),
        )

        captured_payment = {
            "id": "pay_test_123",
            "order_id": "order_test_123",
            "amount": 86900,
            "currency": "INR",
            "status": "captured",
        }

        class FakePayment:
            def fetch(self, payment_id):
                return {**captured_payment, "status": "authorized"}

            def capture(self, payment_id, amount, options):
                assert amount == 86900
                assert options == {"currency": "INR"}
                return captured_payment

        fake_client = SimpleNamespace(
            order=SimpleNamespace(
                create=lambda data: {
                    "id": "order_test_123",
                    "amount": data["amount"],
                    "currency": data["currency"],
                }
            ),
            payment=FakePayment(),
        )
        monkeypatch.setattr(
            "apps.payments.services.get_razorpay_client",
            lambda: fake_client,
        )
        monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "test_key", raising=False)
        monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret", raising=False)
        api_client.force_authenticate(user=customer.user)

        response = api_client.post(
            "/api/payments/create/",
            {"order_id": str(order.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount"] == 86900

        signature = hmac.new(
            b"test_secret",
            b"order_test_123|pay_test_123",
            hashlib.sha256,
        ).hexdigest()
        response = api_client.post(
            "/api/payments/verify/",
            {
                "razorpay_order_id": "order_test_123",
                "razorpay_payment_id": "pay_test_123",
                "razorpay_signature": signature,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.payment_status == Order.PaymentStatus.PAID
        assert order.status == Order.Status.CONFIRMED
        assert Payment.objects.get(order=order).status == Payment.Status.CAPTURED

    def test_webhook_signature_uses_exact_request_body(self, api_client, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "webhook_secret", raising=False)
        body = b'{ "event": "ignored", "payload": {} }'
        signature = hmac.new(
            b"webhook_secret",
            body,
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            "/api/payments/webhook/razorpay/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )
        assert response.status_code == status.HTTP_200_OK

        response = api_client.post(
            "/api/payments/webhook/razorpay/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
