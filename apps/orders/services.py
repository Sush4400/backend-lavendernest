"""Business logic for order placement, validation, and management."""

import logging
from decimal import Decimal
from django.db import transaction
from django.conf import settings

from apps.products.models import Product, Cart, CartItem
from apps.users.models import Address
from apps.inventory.services import record_inventory_deduction
from .models import Order, OrderItem

logger = logging.getLogger(__name__)

SHIPPING_FREE_THRESHOLD = Decimal("499.00")
SHIPPING_COST = Decimal("60.00")
TAX_RATE = Decimal("0.00")  # GST handled separately if needed


def calculate_shipping(subtotal: Decimal) -> Decimal:
    """Free shipping above threshold, else flat rate."""
    return Decimal("0") if subtotal >= SHIPPING_FREE_THRESHOLD else SHIPPING_COST


def validate_cart_for_checkout(cart: Cart) -> list[dict]:
    """
    Validate all cart items against current stock.
    Returns list of validation errors (empty if all OK).
    """
    errors = []
    for item in cart.items.select_related("product").all():
        product = item.product
        if product.status != Product.Status.ACTIVE:
            errors.append({
                "product": product.name,
                "error": "Product is no longer available.",
            })
        elif item.quantity > product.stock:
            errors.append({
                "product": product.name,
                "error": f"Only {product.stock} unit(s) available, you have {item.quantity} in cart.",
            })
    return errors


@transaction.atomic
def place_order(customer, address_id: int, notes: str = "") -> Order:
    """
    Place an order from the customer's cart.
    - Validates stock with row-level locking
    - Creates Order and OrderItems
    - Deducts inventory
    - Clears the cart
    - Returns the placed Order
    """
    try:
        address = Address.objects.get(id=address_id, customer=customer)
    except Address.DoesNotExist:
        raise ValueError("Shipping address not found.")

    try:
        cart = Cart.objects.prefetch_related("items__product").get(customer=customer)
    except Cart.DoesNotExist:
        raise ValueError("Your cart is empty.")

    if not cart.items.exists():
        raise ValueError("Your cart is empty.")

    # Lock product rows to prevent race conditions
    product_ids = [item.product_id for item in cart.items.all()]
    products = {
        str(p.id): p
        for p in Product.objects.select_for_update().filter(id__in=product_ids)
    }

    # Validate stock
    for item in cart.items.all():
        product = products[str(item.product_id)]
        if product.status != Product.Status.ACTIVE:
            raise ValueError(f"'{product.name}' is no longer available.")
        if item.quantity > product.stock:
            raise ValueError(
                f"Only {product.stock} unit(s) of '{product.name}' available."
            )

    # Calculate totals (server-side only)
    subtotal = sum(item.quantity * products[str(item.product_id)].price for item in cart.items.all())
    shipping_cost = calculate_shipping(subtotal)
    tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
    total_amount = subtotal + shipping_cost + tax_amount

    # Create the order
    order = Order.objects.create(
        customer=customer,
        shipping_full_name=address.full_name,
        shipping_phone=address.phone_number,
        shipping_address_line1=address.address_line1,
        shipping_address_line2=address.address_line2,
        shipping_city=address.city,
        shipping_state=address.state,
        shipping_postal_code=address.postal_code,
        shipping_country=address.country,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=notes,
    )

    # Create order items and deduct inventory
    for item in cart.items.all():
        product = products[str(item.product_id)]
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=product.price,
            quantity=item.quantity,
        )
        # Deduct stock
        product.stock -= item.quantity
        product.save(update_fields=["stock", "updated_at"])
        record_inventory_deduction(product, item.quantity, f"Order {order.order_number}")

    # Clear the cart
    cart.items.all().delete()

    logger.info(
        "Order %s placed by %s. Total: ₹%s",
        order.order_number,
        customer.user.email,
        order.total_amount,
    )
    return order


def cancel_order(order: Order, cancelled_by_user=False) -> Order:
    """Cancel an order and restore inventory."""
    cancellable_statuses = [Order.Status.PENDING, Order.Status.CONFIRMED]
    if order.status not in cancellable_statuses:
        raise ValueError(f"Order in '{order.get_status_display()}' status cannot be cancelled.")

    with transaction.atomic():
        for item in order.items.select_related("product").all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save(update_fields=["stock", "updated_at"])
                record_inventory_deduction(
                    item.product, -item.quantity, f"Cancellation of Order {order.order_number}"
                )

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

    logger.info("Order %s cancelled.", order.order_number)
    return order
