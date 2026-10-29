"""Shared pytest fixtures for the LavenderNest test suite."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.users.models import Customer

User = get_user_model()


# ─── Clients ────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(customer_user):
    """An APIClient authenticated as a regular customer."""
    client = APIClient()
    client.force_authenticate(user=customer_user)
    return client


@pytest.fixture
def staff_client(staff_user):
    """An APIClient authenticated as a staff user."""
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


# ─── Users ──────────────────────────────────────────────────────────────────

@pytest.fixture
def customer_user(db):
    user = User.objects.create_user(
        email="customer@lavendernest.in",
        password="CustomerPass123!",
        first_name="Aarushi",
        last_name="Mehta",
        role=User.Role.CUSTOMER,
    )
    Customer.objects.get_or_create(user=user)
    return user


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@lavendernest.in",
        password="StaffPass123!",
        first_name="Store",
        last_name="Manager",
        role=User.Role.STAFF,
        is_staff=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@lavendernest.in",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


# ─── Product catalogue ───────────────────────────────────────────────────────

@pytest.fixture
def category(db):
    return Category.objects.create(
        name="Scented Candles",
        slug="candles",
        description="Hand-poured soy candles.",
        is_active=True,
    )


@pytest.fixture
def inactive_category(db):
    return Category.objects.create(
        name="Archived",
        slug="archived",
        is_active=False,
    )


@pytest.fixture
def product(db, category):
    return Product.objects.create(
        name="Lavender Dreams Candle",
        sku="CNDL-TEST-001",
        category=category,
        price="349.00",
        compare_at_price="429.00",
        stock=50,
        status=Product.Status.ACTIVE,
        is_featured=True,
        short_description="A calming lavender candle.",
        description="Full description here.",
        tags="lavender,soy,gift",
    )


@pytest.fixture
def out_of_stock_product(db, category):
    return Product.objects.create(
        name="Sold Out Candle",
        sku="CNDL-TEST-OOS",
        category=category,
        price="199.00",
        stock=0,
        status=Product.Status.ACTIVE,
        description="Out of stock product.",
    )


@pytest.fixture
def draft_product(db, category):
    return Product.objects.create(
        name="Unreleased Candle",
        sku="CNDL-TEST-DRAFT",
        category=category,
        price="250.00",
        stock=5,
        status=Product.Status.DRAFT,
        description="Draft product.",
    )

