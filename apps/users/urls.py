"""URL routing for the users app."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "users"

urlpatterns = [
    # Authentication
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # Profile
    path("me/", views.ProfileView.as_view(), name="profile"),
    path("me/change-password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("me/customer-profile/", views.CustomerProfileView.as_view(), name="customer_profile"),
    # Addresses
    path("me/addresses/", views.AddressListCreateView.as_view(), name="address_list"),
    path("me/addresses/<int:pk>/", views.AddressDetailView.as_view(), name="address_detail"),
]
