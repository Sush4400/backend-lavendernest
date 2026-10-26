"""URL routing for the orders app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.OrderViewSet, basename="order")

app_name = "orders"

urlpatterns = [
    path("", include(router.urls)),
]
