"""
InventoryMovement model for tracking all stock changes.
"""

from django.db import models
from apps.products.models import Product


class InventoryMovement(models.Model):
    """
    Records every stock addition, deduction, or adjustment
    for audit trail and reporting.
    """

    class MovementType(models.TextChoices):
        ADDITION = "addition", "Stock Addition"
        DEDUCTION = "deduction", "Stock Deduction (Sale)"
        ADJUSTMENT = "adjustment", "Manual Adjustment"
        RETURN = "return", "Return / Refund"
        DAMAGE = "damage", "Damage / Loss"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="inventory_movements"
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.IntegerField(
        help_text="Positive for addition, negative for deduction"
    )
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    reference = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Order number, manual note, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inventory Movement"
        verbose_name_plural = "Inventory Movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["movement_type"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.product.name}: {sign}{self.quantity_change} ({self.get_movement_type_display()})"
