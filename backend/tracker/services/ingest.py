"""Handles one message forwarded from the treasurer's phone."""
import logging

from django.conf import settings
from django.db import IntegrityError, transaction

from ..models import IncomingMessage, Payment
from . import matching
from .notify import dispatch, notify_payment
from .parser import parse_mpesa_message, sanitize_message

logger = logging.getLogger(__name__)


def process_incoming(sender, text):
    """Return a short status string: ignored, unparsed, not_mission, duplicate, recorded, review, unassigned."""
    sender = str(sender or "").strip()
    text = str(text or "")

    if sender.lower() not in settings.ALLOWED_SENDERS:
        IncomingMessage.objects.create(sender=sender[:40], status="ignored")
        return "ignored"

    parsed = parse_mpesa_message(text)
    if parsed is None:
        IncomingMessage.objects.create(sender=sender[:40], status="unparsed", text=sanitize_message(text))
        return "unparsed"

    # Tithes and other church payments share the Paybill: only the mission account counts.
    if settings.ACCOUNT_KEYWORD not in parsed.account.lower():
        IncomingMessage.objects.create(sender=sender[:40], status="not_mission", detail=parsed.code)
        return "not_mission"

    if Payment.objects.filter(mpesa_code=parsed.code).exists():
        IncomingMessage.objects.create(sender=sender[:40], status="duplicate", detail=parsed.code)
        return "duplicate"

    result = matching.find_member(parsed.payer_phone, parsed.payer_name)
    if result.member and result.how in (matching.PHONE, matching.NAME):
        status, member, suggested = Payment.RECORDED, result.member, None
    elif result.member and result.how == matching.CLOSE:
        status, member, suggested = Payment.REVIEW, None, result.member
    else:
        status, member, suggested = Payment.UNASSIGNED, None, None

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                mpesa_code=parsed.code,
                amount=parsed.amount,
                payer_name=parsed.payer_name,
                payer_phone=parsed.payer_phone,
                account_text=parsed.account,
                paid_at=parsed.paid_at,
                member=member,
                suggested_member=suggested,
                status=status,
                source="sms",
                raw_message=sanitize_message(text),
            )
            if status == Payment.RECORDED:
                dispatch(notify_payment, payment.pk)
    except IntegrityError:
        IncomingMessage.objects.create(sender=sender[:40], status="duplicate", detail=parsed.code)
        return "duplicate"

    IncomingMessage.objects.create(sender=sender[:40], status=status, detail=parsed.code)
    return status
