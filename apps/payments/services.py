"""Razorpay payment service layer."""

import hashlib
import hmac
import json
import logging
from decimal import Decimal

import razorpay
from django.conf import settings
from django.db import transaction
from razorpay.errors import BadRequestError, GatewayError, ServerError

from apps.orders.models import Order
from .models import Payment

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Raised when Razorpay cannot verify or capture a payment."""


def get_razorpay_client():
    """Return an authenticated Razorpay client."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay credentials are not configured.")
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
    if not settings.RAZORPAY_KEY_SECRET:
        return False
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
    Verify the callback and confirm the gateway's payment state and amount.
    Updates Order payment_status to PAID.
    """
    try:
        payment = Payment.objects.select_for_update().get(
            razorpay_order_id=razorpay_order_id
        )
    except Payment.DoesNotExist:
        raise ValueError(f"No payment found for Razorpay order: {razorpay_order_id}")

    if payment.provider != Payment.Provider.RAZORPAY:
        raise ValueError("This payment was not created with Razorpay.")
    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise ValueError("Payment signature verification failed.")

    order = Order.objects.select_for_update().get(pk=payment.order_id)
    if order.status in (Order.Status.CANCELLED, Order.Status.REFUNDED):
        raise ValueError("This order can no longer be paid.")

    if (
        payment.status == Payment.Status.CAPTURED
        and payment.razorpay_payment_id != razorpay_payment_id
    ):
        raise ValueError("A different payment has already been captured for this order.")

    client = get_razorpay_client()
    expected_amount = int(payment.amount * 100)
    try:
        gateway_payment = client.payment.fetch(razorpay_payment_id)
    except (BadRequestError, GatewayError, ServerError) as exc:
        logger.exception("Razorpay payment lookup failed for order %s", order.order_number)
        raise PaymentGatewayError("Payment gateway verification failed.") from exc
    if (
        gateway_payment.get("order_id") != razorpay_order_id
        or gateway_payment.get("amount") != expected_amount
        or gateway_payment.get("currency") != payment.currency
    ):
        raise ValueError("Payment details do not match the order.")

    if gateway_payment.get("status") == "authorized":
        try:
            gateway_payment = client.payment.capture(
                razorpay_payment_id,
                expected_amount,
                {"currency": payment.currency},
            )
        except (BadRequestError, GatewayError, ServerError) as exc:
            logger.exception("Razorpay capture failed for order %s", order.order_number)
            raise PaymentGatewayError("The payment could not be captured.") from exc
    elif gateway_payment.get("status") != "captured":
        raise ValueError("The payment has not been captured.")
    if gateway_payment.get("status") != "captured":
        raise ValueError("The payment could not be captured.")

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = Payment.Status.CAPTURED
    payment.gateway_response = gateway_payment
    payment.save(update_fields=[
        "razorpay_payment_id",
        "razorpay_signature",
        "status",
        "gateway_response",
        "updated_at",
    ])

    # Update order payment and status
    order.payment_status = Order.PaymentStatus.PAID
    update_fields = ["payment_status", "updated_at"]
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.CONFIRMED
        update_fields.append("status")
    order.save(update_fields=update_fields)

    logger.info(
        "Payment captured for order %s. Razorpay payment ID: %s",
        order.order_number,
        razorpay_payment_id,
    )
    return payment


@transaction.atomic
def process_webhook(
    payload: dict,
    razorpay_signature: str,
    raw_body: str | None = None,
) -> None:
    """
    Process Razorpay webhook events.
    Handles payment.captured and payment.failed events.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise ValueError("Razorpay webhook secret is not configured.")
    body = raw_body if raw_body is not None else json.dumps(payload, separators=(",", ":"))
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, razorpay_signature):
        logger.warning("Webhook signature verification failed.")
        raise ValueError("Invalid webhook signature.")

    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object.")
    event = payload.get("event")
    event_payload = payload.get("payload", {})
    payment_data = event_payload.get("payment", {}) if isinstance(event_payload, dict) else {}
    payment_entity = payment_data.get("entity", {}) if isinstance(payment_data, dict) else {}
    if event in ("payment.captured", "payment.failed") and not isinstance(payment_entity, dict):
        raise ValueError("Webhook payment payload is invalid.")

    if event == "payment.captured":
        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id")
        try:
            payment = Payment.objects.select_for_update().select_related("order").get(
                razorpay_order_id=razorpay_order_id,
                provider=Payment.Provider.RAZORPAY,
            )
            if (
                payment.status == Payment.Status.CAPTURED
                and payment.razorpay_payment_id != razorpay_payment_id
            ):
                raise ValueError("A different payment has already been captured for this order.")
            if (
                payment_entity.get("amount") != int(payment.amount * 100)
                or payment_entity.get("currency") != payment.currency
            ):
                logger.error("Webhook amount mismatch for Razorpay order %s", razorpay_order_id)
                raise ValueError("Webhook payment details do not match the order.")
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = Payment.Status.CAPTURED
            payment.gateway_response = payload
            payment.save(update_fields=[
                "razorpay_payment_id", "status", "gateway_response", "updated_at"
            ])
            order = payment.order
            order.payment_status = Order.PaymentStatus.PAID
            update_fields = ["payment_status", "updated_at"]
            if order.status == Order.Status.PENDING:
                order.status = Order.Status.CONFIRMED
                update_fields.append("status")
            order.save(update_fields=update_fields)
            logger.info("Webhook: Payment captured for order %s", order.order_number)
        except Payment.DoesNotExist:
            logger.warning("Webhook: Payment not found for Razorpay order %s", razorpay_order_id)

    elif event == "payment.failed":
        razorpay_order_id = payment_entity.get("order_id")
        try:
            payment = Payment.objects.select_for_update().select_related("order").get(
                razorpay_order_id=razorpay_order_id,
                provider=Payment.Provider.RAZORPAY,
            )
            if payment.status != Payment.Status.CAPTURED:
                payment.status = Payment.Status.FAILED
                payment.gateway_response = payload
                payment.save(update_fields=["status", "gateway_response", "updated_at"])
                if payment.order.payment_status != Order.PaymentStatus.PAID:
                    payment.order.payment_status = Order.PaymentStatus.FAILED
                    payment.order.save(update_fields=["payment_status", "updated_at"])
                logger.info("Webhook: Payment failed for order %s", payment.order.order_number)
        except Payment.DoesNotExist:
            logger.warning("Webhook: Payment not found for Razorpay order %s", razorpay_order_id)
