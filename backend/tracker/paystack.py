"""Paystack: start a payment, verify it, and confirm it from the webhook."""
import hashlib
import hmac
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .emails import send_receipt
from .models import Payment

API_URL = "https://api.paystack.co"
# A payment that was only started also reports "abandoned", so give the member time to finish checkout.
CHECKOUT_GRACE = timedelta(minutes=30)

log = logging.getLogger(__name__)


class PaystackError(Exception):
    pass


def _call(method, path, **kwargs):
    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError("PAYSTACK_SECRET_KEY is not set")
    try:
        response = requests.request(
            method,
            API_URL + path,
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=20,
            **kwargs,
        )
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaystackError("Could not reach Paystack") from exc
    if not response.ok or not body.get("status"):
        raise PaystackError(body.get("message") or "Paystack request failed")
    return body["data"]


def _new_payment(member, amount, note=""):
    return Payment.objects.create(
        reference=f"GN27-{uuid.uuid4().hex[:16].upper()}", member=member, amount=amount, note=note
    )


def start_payment(member, amount, note=""):
    """Create a pending payment and return Paystack's checkout URL."""
    payment = _new_payment(member, amount, note)
    payload = {
        "email": member.email,
        "amount": int(Decimal(amount) * 100),  # Paystack expects the lowest currency unit
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": payment.reference,
        "metadata": {"member_code": member.code, "member_name": member.name},
    }
    if settings.PAYSTACK_CALLBACK_URL:
        payload["callback_url"] = settings.PAYSTACK_CALLBACK_URL
    try:
        data = _call("POST", "/transaction/initialize", json=payload)
    except PaystackError:
        payment.status = Payment.FAILED
        payment.save(update_fields=["status"])
        raise
    return payment, data["authorization_url"]


def mpesa_prompt(member, amount, note=""):
    """Ask Paystack to send an M-Pesa PIN prompt to the member's phone. The webhook or a sync confirms it."""
    payment = _new_payment(member, amount, note)
    payload = {
        "email": member.email,
        "amount": int(Decimal(amount) * 100),
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": payment.reference,
        "mobile_money": {"phone": f"+{member.phone}", "provider": "mpesa"},
        "metadata": {"member_code": member.code, "member_name": member.name},
    }
    try:
        data = _call("POST", "/charge", json=payload)
    except PaystackError:
        payment.status = Payment.FAILED
        payment.save(update_fields=["status"])
        raise
    return payment, data.get("display_text") or "Check your phone and enter your M-Pesa PIN."


def valid_signature(raw_body, signature):
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return bool(settings.PAYSTACK_SECRET_KEY) and hmac.compare_digest(expected, signature or "")


def apply_transaction(data):
    """Update our payment from a Paystack transaction object. Safe to call more than once."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(reference=data.get("reference")).first()
        if not payment or payment.status != Payment.PENDING:
            return payment

        expected = int(payment.amount * 100)
        same_money = data.get("amount") == expected and data.get("currency") == settings.PAYSTACK_CURRENCY
        if data.get("status") == "success" and same_money:
            payment.status = Payment.SUCCESS
            payment.channel = data.get("channel") or ""
            payment.paid_at = parse_datetime(data.get("paid_at") or "") or timezone.now()
            transaction.on_commit(lambda: send_receipt(payment))
        elif data.get("status") in ("failed", "abandoned", "reversed") or not same_money:
            payment.status = Payment.FAILED
        else:
            return payment  # still in progress
        payment.save()
    return payment


def verify_payment(reference):
    return apply_transaction(_call("GET", f"/transaction/verify/{reference}"))


def sync_pending(payments, limit=10):
    """Ask Paystack about pending payments, in case the callback and webhook never reached us."""
    pending = payments.filter(status=Payment.PENDING, source="paystack").order_by("-created_at")[:limit]
    for payment in pending:
        try:
            data = _call("GET", f"/transaction/verify/{payment.reference}")
        except PaystackError as exc:
            log.warning("Could not verify %s: %s", payment.reference, exc)
            continue
        if data.get("status") == "success" or timezone.now() - payment.created_at > CHECKOUT_GRACE:
            apply_transaction(data)
