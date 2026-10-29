"""Tests for the products app."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.products.models import Category, Product

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@lavendernest.in",
        password="StaffPass123!",
        role=User.Role.STAFF,
        is_staff=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Candles", slug="candles", is_active=True)


@pytest.fixture
def product(db, category):
    return Product.objects.create(
        name="Lavender Candle",
        sku="CNDL-001",
        category=category,
        price=299.00,
        stock=50,
        status=Product.Status.ACTIVE,
        description="A beautiful lavender-scented candle.",
    )


@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories(self, api_client, category):
        response = api_client.get("/api/products/categories/")
        assert response.status_code == status.HTTP_200_OK

    def test_create_category_as_staff(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.post("/api/products/categories/", {
            "name": "Gift Sets",
            "slug": "gift-sets",
            "description": "Handcrafted gift sets",
            "is_active": True,
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_category_as_anon_fails(self, api_client):
        response = api_client.post("/api/products/categories/", {"name": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_category_is_staff_only(self, api_client, staff_user):
        category = Category.objects.create(
            name="Archived Decor",
            slug="archived-decor",
            is_active=False,
        )
        response = api_client.get(f"/api/products/categories/{category.slug}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        api_client.force_authenticate(user=staff_user)
        response = api_client.get(f"/api/products/categories/{category.slug}/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProductAPI:
    def test_list_active_products(self, api_client, product):
        response = api_client.get("/api/products/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_product_detail(self, api_client, product):
        response = api_client.get(f"/api/products/{product.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == product.name

    def test_product_filter_by_category_slug(self, api_client, product):
        response = api_client.get("/api/products/?category_slug=candles")
        assert response.status_code == status.HTTP_200_OK

    def test_product_price_filter(self, api_client, product):
        response = api_client.get("/api/products/?min_price=100&max_price=500")
        assert response.status_code == status.HTTP_200_OK
