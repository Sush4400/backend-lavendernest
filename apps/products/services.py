"""Cart ownership helpers."""

import logging

from django.db import transaction

from apps.users.models import Customer
from .models import Cart, CartItem, Product

logger = logging.getLogger(__name__)


def get_cart_for_request(request) -> Cart:
    """Return a cart owned by the authenticated customer or current session."""
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        cart, _ = Cart.objects.get_or_create(customer=customer)
        session_key = request.session.session_key
        if session_key:
            merge_guest_cart(cart, session_key)
        return cart

    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


@transaction.atomic
def merge_guest_cart(customer_cart: Cart, session_key: str) -> None:
    """Merge a browser's session cart into its customer cart after sign-in."""
    guest_carts = Cart.objects.filter(session_key=session_key).exclude(pk=customer_cart.pk)
    for guest_cart in guest_carts:
        for guest_item in guest_cart.items.select_related("product").all():
            product = Product.objects.select_for_update().filter(
                pk=guest_item.product_id, status=Product.Status.ACTIVE
            ).first()
            if not product or product.stock == 0:
                continue
            item, created = CartItem.objects.get_or_create(
                cart=customer_cart,
                product=product,
                defaults={"quantity": min(guest_item.quantity, product.stock)},
            )
            if not created:
                item.quantity = min(item.quantity + guest_item.quantity, product.stock)
                item.save(update_fields=["quantity"])
        guest_cart.delete()
    logger.info("Merged guest cart into customer cart %s", customer_cart.pk)
