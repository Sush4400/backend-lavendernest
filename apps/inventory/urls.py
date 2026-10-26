"""URL routing for the inventory app."""

from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("movements/", views.InventoryMovementListView.as_view(), name="movement_list"),
    path("movements/product/<uuid:product_id>/", views.ProductInventoryMovementView.as_view(), name="product_movements"),
    path("stock/add/", views.AddStockView.as_view(), name="add_stock"),
    path("stock/adjust/", views.AdjustStockView.as_view(), name="adjust_stock"),
    path("low-stock/", views.LowStockView.as_view(), name="low_stock"),
]
