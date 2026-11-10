"""Tests for the users app."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def make_user(**kwargs):
        defaults = {
            "email": "test@lavendernest.in",
            "password": "TestPass123!",
            "first_name": "Lavender",
            "last_name": "User",
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    return make_user


@pytest.mark.django_db
class TestUserRegistration:
    def test_register_success(self, api_client):
        data = {
            "email": "new@lavendernest.in",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert response.data["user"]["email"] == data["email"]

    def test_register_mismatched_passwords(self, api_client):
        data = {
            "email": "bad@example.com",
            "first_name": "Bad",
            "last_name": "User",
            "password": "SecurePass123!",
            "password2": "WrongPass123!",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, create_user):
        create_user(email="dup@lavendernest.in")
        data = {
            "email": "dup@lavendernest.in",
            "first_name": "Dup",
            "last_name": "User",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_rejects_case_variant_of_existing_email(self, api_client, create_user):
        create_user(email="existing@example.com")
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "EXISTING@example.com",
                "first_name": "Duplicate",
                "last_name": "User",
                "password": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    def test_login_success(self, api_client, create_user):
        create_user(email="login@test.com", password="TestPass123!")
        response = api_client.post("/api/auth/login/", {
            "email": "login@test.com",
            "password": "TestPass123!",
        })
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_normalizes_email_case(self, api_client, create_user):
        create_user(email="login@test.com", password="TestPass123!")
        response = api_client.post("/api/auth/login/", {
            "email": "LOGIN@TEST.COM",
            "password": "TestPass123!",
        })
        assert response.status_code == status.HTTP_200_OK

    def test_login_wrong_password(self, api_client, create_user):
        create_user(email="user@test.com", password="CorrectPass123!")
        response = api_client.post("/api/auth/login/", {
            "email": "user@test.com",
            "password": "WrongPass123!",
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    def test_get_profile_authenticated(self, api_client, create_user):
        user = create_user()
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_get_profile_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_success(self, api_client, create_user):
        user = create_user(email="changepw@test.com", password="OldPassword123!")
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/auth/me/change-password/", {
            "old_password": "OldPassword123!",
            "new_password": "NewStrongPass2026!",
            "new_password2": "NewStrongPass2026!",
        })
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        user.refresh_from_db()
        assert user.check_password("NewStrongPass2026!")

    def test_change_password_wrong_old_password(self, api_client, create_user):
        user = create_user(email="wrongpw@test.com", password="OldPassword123!")
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/auth/me/change-password/", {
            "old_password": "WrongPassword123!",
            "new_password": "NewStrongPass2026!",
            "new_password2": "NewStrongPass2026!",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_change_password_accepts_aliases(self, api_client, create_user):
        user = create_user(email="aliases@test.com", password="OldPassword123!")
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/auth/me/change-password/", {
            "current_password": "OldPassword123!",
            "new_password": "NewStrongPass2026!",
            "confirm_password": "NewStrongPass2026!",
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("NewStrongPass2026!")
