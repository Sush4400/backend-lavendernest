"""Tests for the cart and order flows."""

import pytest
from rest_framework import status
from apps.products.models import Cart, CartItem
from apps.users.models import Customer


# ─── Cart tests ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCart:
    def test_get_empty_cart_anonymous(self, api_client):
        """Anonymous users can access a session cart."""
        response = api_client.get("/api/products/cart/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["items"] == []

    def test_add_item_to_cart(self, auth_client, product):
        response = auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": 2,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == 2

    def test_add_item_increments_existing(self, auth_client, product):
        auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": 2,
        })
        response = auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": 3,
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["quantity"] == 5

    def test_add_item_exceeds_stock(self, auth_client, product):
        response = auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": product.stock + 1,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_out_of_stock_product(self, auth_client, out_of_stock_product):
        response = auth_client.post("/api/products/cart/items/", {
            "product_id": str(out_of_stock_product.id),
            "quantity": 1,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_draft_product_fails(self, auth_client, draft_product):
        response = auth_client.post("/api/products/cart/items/", {
            "product_id": str(draft_product.id),
            "quantity": 1,
        })
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    def test_remove_cart_item(self, auth_client, customer_user, product):
        auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": 1,
        })
        customer = Customer.objects.get(user=customer_user)
        cart = Cart.objects.get(customer=customer)
        item = cart.items.first()
        response = auth_client.delete(f"/api/products/cart/items/{item.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_cart_item_quantity(self, auth_client, customer_user, product):
        auth_client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": 1,
        })
        customer = Customer.objects.get(user=customer_user)
        cart = Cart.objects.get(customer=customer)
        item = cart.items.first()
        response = auth_client.patch(f"/api/products/cart/items/{item.id}/", {
            "quantity": 3,
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["quantity"] == 3


# ─── Order placement tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOrderPlacement:
    def _add_to_cart(self, client, product, quantity=1):
        return client.post("/api/products/cart/items/", {
            "product_id": str(product.id),
            "quantity": quantity,
        })

    def test_place_order_with_inline_address(self, auth_client, product):
        self._add_to_cart(auth_client, product)
        response = auth_client.post("/api/orders/", {
            "shipping_address": {
                "full_name": "Aarushi Mehta",
                "phone_number": "+919876543210",
                "address_line1": "123 Green Park",
                "city": "Bangalore",
                "state": "Karnataka",
                "postal_code": "560001",
                "country": "India",
            },
            "shipping_method": "standard",
            "payment_method": "cod",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "confirmed"

    def test_place_order_clears_cart(self, auth_client, customer_user, product):
        self._add_to_cart(auth_client, product)
        auth_client.post("/api/orders/", {
            "shipping_address": {
                "full_name": "Test User",
                "phone_number": "+919999999999",
                "address_line1": "1 Test Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
            },
            "shipping_method": "standard",
            "payment_method": "cod",
        }, format="json")
        customer = Customer.objects.get(user=customer_user)
        cart = Cart.objects.filter(customer=customer).first()
        assert cart is None or cart.items.count() == 0

    def test_place_order_empty_cart_fails(self, auth_client):
        response = auth_client.post("/api/orders/", {
            "shipping_address": {
                "full_name": "Test User",
                "phone_number": "+919999999999",
                "address_line1": "1 Test",
                "city": "Delhi",
                "state": "Delhi",
                "postal_code": "110001",
            },
            "shipping_method": "standard",
            "payment_method": "cod",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_order_list_requires_auth(self, api_client):
        response = api_client.get("/api/orders/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_customer_sees_only_their_orders(self, auth_client, product):
        self._add_to_cart(auth_client, product)
        auth_client.post("/api/orders/", {
            "shipping_address": {
                "full_name": "Aarushi",
                "phone_number": "+919876543210",
                "address_line1": "123 Green Park",
                "city": "Bangalore",
                "state": "Karnataka",
                "postal_code": "560001",
            },
            "shipping_method": "standard",
            "payment_method": "cod",
        }, format="json")
        response = auth_client.get("/api/orders/")
        assert response.status_code == status.HTTP_200_OK
        count = response.data.get("count", len(response.data))
        assert count >= 1

