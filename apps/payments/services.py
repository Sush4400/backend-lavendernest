"""Razorpay payment service layer."""

import hashlib
import hmac
import logging
from decimal import Decimal

import razorpay
from django.conf import settings
from django.db import transaction

from apps.orders.models import Order
from .models import Payment

logger = logging.getLogger(__name__)


def get_razorpay_client():
    """Return an authenticated Razorpay client."""
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(order: Order) -> dict:
    """
    Create a Razorpay order for the given Order.
    Returns the Razorpay order data dict.
    """
    client = get_razorpay_client()

    # Amount in paise (smallest currency unit)
    amount_paise = int(order.total_amount * 100)

    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": order.order_number,
        "notes": {
            "order_id": str(order.id),
            "customer_email": order.customer.user.email,
        },
    })

    # Create or update Payment record
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "amount": order.total_amount,
            "razorpay_order_id": razorpay_order["id"],
            "status": Payment.Status.CREATED,
            "gateway_response": razorpay_order,
        }
    )
    if not created:
        payment.razorpay_order_id = razorpay_order["id"]
        payment.gateway_response = razorpay_order
        payment.save(update_fields=["razorpay_order_id", "gateway_response", "updated_at"])

    logger.info("Razorpay order created: %s for order %s", razorpay_order["id"], order.order_number)
    return razorpay_order


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify the Razorpay payment signature using HMAC-SHA256.
    Returns True if the signature is valid.
    """
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, razorpay_signature)


@transaction.atomic
def capture_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> Payment:
    """
    Verify signature and mark payment as captured.
    Updates Order payment_status to PAID.
    """
    try:
        payment = Payment.objects.select_for_update().get(
            razorpay_order_id=razorpay_order_id
        )
    except Payment.DoesNotExist:
        raise ValueError(f"No payment found for Razorpay order: {razorpay_order_id}")

    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise ValueError("Payment signature verification failed.")

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = Payment.Status.CAPTURED
    payment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status", "updated_at"])

    # Update order payment and status
    order = payment.order
    order.payment_status = Order.PaymentStatus.PAID
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["payment_status", "status", "updated_at"])

    logger.info(
        "Payment captured for order %s. Razorpay payment ID: %s",
        order.order_number,
        razorpay_payment_id,
    )
    return payment


def process_webhook(payload: dict, razorpay_signature: str) -> None:
    """
    Process Razorpay webhook events.
    Handles payment.captured and payment.failed events.
    """
    import json
    client = get_razorpay_client()

    try:
        client.utility.verify_webhook_signature(
            json.dumps(payload, separators=(",", ":")),
            razorpay_signature,
            settings.RAZORPAY_KEY_SECRET,
        )
    except Exception:
        logger.warning("Webhook signature verification failed.")
        raise ValueError("Invalid webhook signature.")

    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    if event == "payment.captured":
        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id")
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = Payment.Status.CAPTURED
            payment.gateway_response = payload
            payment.save()
            order = payment.order
            order.payment_status = Order.PaymentStatus.PAID
            order.status = Order.Status.CONFIRMED
            order.save(update_fields=["payment_status", "status"])
            logger.info("Webhook: Payment captured for order %s", order.order_number)
        except Payment.DoesNotExist:
            logger.warning("Webhook: Payment not found for Razorpay order %s", razorpay_order_id)

    elif event == "payment.failed":
        razorpay_order_id = payment_entity.get("order_id")
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.status = Payment.Status.FAILED
            payment.gateway_response = payload
            payment.save()
            logger.info("Webhook: Payment failed for order %s", payment.order.order_number)
        except Payment.DoesNotExist:
            pass
