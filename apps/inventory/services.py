"""Inventory management service functions."""

import logging
from django.conf import settings
from apps.products.models import Product
from .models import InventoryMovement

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = getattr(settings, "LOW_STOCK_THRESHOLD", 5)


def record_inventory_deduction(product: Product, quantity: int, reference: str = "") -> InventoryMovement:
    """Record a stock deduction (order fulfillment or cancellation restore)."""
    stock_before = product.stock + quantity  # stock was already updated on product
    movement = InventoryMovement.objects.create(
        product=product,
        movement_type=(
            InventoryMovement.MovementType.RETURN
            if quantity < 0
            else InventoryMovement.MovementType.DEDUCTION
        ),
        quantity_change=-quantity,
        stock_before=stock_before,
        stock_after=product.stock,
        reference=reference,
    )

    # Low stock alert
    if product.stock <= LOW_STOCK_THRESHOLD:
        logger.warning(
            "LOW STOCK ALERT: '%s' has only %d unit(s) remaining.",
            product.name,
            product.stock,
        )

    return movement


def add_stock(product: Product, quantity: int, reference: str = "") -> InventoryMovement:
    """Add stock to a product and record the movement."""
    stock_before = product.stock
    product.stock += quantity
    product.save(update_fields=["stock", "updated_at"])

    movement = InventoryMovement.objects.create(
        product=product,
        movement_type=InventoryMovement.MovementType.ADDITION,
        quantity_change=quantity,
        stock_before=stock_before,
        stock_after=product.stock,
        reference=reference,
    )
    logger.info("Stock added: %d units to '%s'. New stock: %d", quantity, product.name, product.stock)
    return movement


def adjust_stock(product: Product, new_quantity: int, reference: str = "") -> InventoryMovement:
    """Manually adjust stock to a specific value."""
    stock_before = product.stock
    quantity_change = new_quantity - stock_before
    product.stock = new_quantity
    product.save(update_fields=["stock", "updated_at"])

    movement = InventoryMovement.objects.create(
        product=product,
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        quantity_change=quantity_change,
        stock_before=stock_before,
        stock_after=product.stock,
        reference=reference,
    )
    logger.info(
        "Stock adjusted for '%s': %d → %d (change: %+d)",
        product.name, stock_before, new_quantity, quantity_change,
    )
    return movement


def get_low_stock_products(threshold: int = None):
    """Return all products below the low stock threshold."""
    threshold = threshold or LOW_STOCK_THRESHOLD
    return Product.objects.filter(
        stock__lte=threshold,
        status=Product.Status.ACTIVE,
    ).order_by("stock")
