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

SHIPPING_FREE_THRESHOLD = Decimal("1000.00")
SHIPPING_COST = Decimal("70.00")
EXPRESS_SHIPPING_COST = Decimal("120.00")
TAX_RATE = Decimal("0.00")  # GST handled separately if needed
PROMO_CODE = "NEST10"
PROMO_DISCOUNT_RATE = Decimal("0.10")


def calculate_shipping(subtotal: Decimal, shipping_method: str = "standard") -> Decimal:
    """Calculate delivery charges using the storefront's INR pricing."""
    if shipping_method == "express":
        return EXPRESS_SHIPPING_COST
    return Decimal("0") if subtotal >= SHIPPING_FREE_THRESHOLD else SHIPPING_COST


def calculate_discount(subtotal: Decimal, coupon_code: str = "") -> Decimal:
    """Apply the supported demo promotion or reject an unknown code."""
    if not coupon_code:
        return Decimal("0.00")
    if coupon_code.strip().upper() != PROMO_CODE:
        raise ValueError("Invalid promo code.")
    return (subtotal * PROMO_DISCOUNT_RATE).quantize(Decimal("0.01"))


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
def place_order(
    customer,
    address_id: int | None = None,
    shipping_address: dict | None = None,
    notes: str = "",
    shipping_method: str = Order.ShippingMethod.STANDARD,
    payment_method: str = Order.PaymentMethod.RAZORPAY,
    coupon_code: str = "",
    save_address: bool = False,
) -> Order:
    """
    Place an order from the customer's cart.
    - Validates stock with row-level locking
    - Creates Order and OrderItems
    - Deducts inventory
    - Clears the cart
    - Returns the placed Order
    """
    if address_id is not None:
        try:
            address = Address.objects.get(id=address_id, customer=customer)
        except Address.DoesNotExist:
            raise ValueError("Shipping address not found.")
    elif shipping_address:
        address = None
        if save_address:
            address = Address.objects.create(customer=customer, **shipping_address)
    else:
        raise ValueError("A shipping address is required.")

    try:
        cart = Cart.objects.select_for_update().get(customer=customer)
    except Cart.DoesNotExist:
        raise ValueError("Your cart is empty.")

    cart_items = list(cart.items.select_related("product").all())
    if not cart_items:
        raise ValueError("Your cart is empty.")

    # Lock product rows to prevent race conditions
    product_ids = [item.product_id for item in cart_items]
    products = {
        str(p.id): p
        for p in Product.objects.select_for_update().filter(id__in=product_ids).order_by("id")
    }

    # Validate stock
    for item in cart_items:
        product = products[str(item.product_id)]
        if product.status != Product.Status.ACTIVE:
            raise ValueError(f"'{product.name}' is no longer available.")
        if item.quantity > product.stock:
            raise ValueError(
                f"Only {product.stock} unit(s) of '{product.name}' available."
            )

    # Calculate totals (server-side only)
    subtotal = sum(item.quantity * products[str(item.product_id)].price for item in cart_items)
    shipping_cost = calculate_shipping(subtotal, shipping_method)
    discount_amount = calculate_discount(subtotal, coupon_code)
    tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
    total_amount = max(Decimal("0.00"), subtotal + shipping_cost + tax_amount - discount_amount)

    if shipping_address:
        address_values = shipping_address
    else:
        address_values = {
            "full_name": address.full_name,
            "phone_number": address.phone_number,
            "address_line1": address.address_line1,
            "address_line2": address.address_line2,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        }

    # Create the order
    order = Order.objects.create(
        customer=customer,
        shipping_full_name=address_values["full_name"],
        shipping_phone=address_values["phone_number"],
        shipping_address_line1=address_values["address_line1"],
        shipping_address_line2=address_values.get("address_line2", ""),
        shipping_city=address_values["city"],
        shipping_state=address_values["state"],
        shipping_postal_code=address_values["postal_code"],
        shipping_country=address_values.get("country", "India"),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        shipping_method=shipping_method,
        payment_method=payment_method,
        coupon_code=coupon_code.strip().upper(),
        status=(
            Order.Status.CONFIRMED
            if payment_method == Order.PaymentMethod.COD
            else Order.Status.PENDING
        ),
        notes=notes,
    )

    # Create order items and deduct inventory
    for item in cart_items:
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
    cart.items.filter(pk__in=[item.pk for item in cart_items]).delete()

    if payment_method == Order.PaymentMethod.COD:
        from apps.payments.models import Payment
        Payment.objects.create(
            order=order,
            provider=Payment.Provider.COD,
            amount=order.total_amount,
            status=Payment.Status.CREATED,
        )

    logger.info(
        "Order %s placed by %s. Total: ₹%s",
        order.order_number,
        customer.user.email,
        order.total_amount,
    )
    return order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    """Cancel an order and restore inventory."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    cancellable_statuses = [
        Order.Status.PENDING,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
    ]
    if order.status not in cancellable_statuses:
        raise ValueError(f"Order in '{order.get_status_display()}' status cannot be cancelled.")
    if order.payment_status == Order.PaymentStatus.PAID:
        raise ValueError("Paid orders must be refunded before they can be cancelled.")

    items = list(order.items.exclude(product__isnull=True).order_by("product_id"))
    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in items])
        .order_by("pk")
    }
    for item in items:
        product = products.get(item.product_id)
        if product:
            product.stock += item.quantity
            product.save(update_fields=["stock", "updated_at"])
            record_inventory_deduction(
                product, -item.quantity, f"Cancellation of Order {order.order_number}"
            )

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    logger.info("Order %s cancelled.", order.order_number)
    return order
