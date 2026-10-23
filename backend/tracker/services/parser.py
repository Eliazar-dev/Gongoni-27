"""Reads the M-Pesa Paybill confirmation message.

Sample (names and numbers belong to a real test payment):
  UJL11B2KXF Confirmed. on 21/10/26 at 5:33 PM Ksh30.00 received from Belinda Boyani Mayore
  254707548406.  Account Number mission commitment  New Utility balance is Ksh241,585.00
"""
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .phones import normalize_phone

MESSAGE_RE = re.compile(
    r"(?P<code>[A-Z0-9]{10})\s+Confirmed\.?\s*"
    r"(?:on\s+(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(?P<time>\d{1,2}:\d{2}\s*[AP]M)\s*)?"
    r"(?:Ksh|KES)\.?\s*(?P<amount>[\d,]+(?:\.\d+)?)\s+received\s+from\s+"
    r"(?P<payer>.+?)\s*\.?\s+Account\s+(?:Number|No\.?)\s*:?\s*(?P<account>.+?)\s+New\s+Utility\s+balance",
    re.IGNORECASE | re.DOTALL,
)
PHONE_IN_PAYER_RE = re.compile(r"\+?\d[\d*]{8,12}")
BALANCE_RE = re.compile(r"\s*New\s+Utility\s+balance.*$", re.IGNORECASE | re.DOTALL)


@dataclass
class ParsedPayment:
    code: str
    amount: Decimal
    payer_name: str
    payer_phone: str  # normalized 2547..., empty when the number is masked or unreadable
    account: str
    paid_at: datetime


def sanitize_message(text):
    """Remove the church's Utility balance. We never store or show it."""
    return BALANCE_RE.sub("", str(text or "")).strip()


def _parse_datetime(date_text, time_text):
    if not date_text or not time_text:
        return timezone.now()
    time_text = re.sub(r"\s+", " ", time_text.strip().upper())
    if " " not in time_text:
        time_text = time_text[:-2] + " " + time_text[-2:]
    fmt = "%d/%m/%Y" if len(date_text.split("/")[-1]) == 4 else "%d/%m/%y"
    try:
        naive = datetime.strptime(f"{date_text} {time_text}", f"{fmt} %I:%M %p")
    except ValueError:
        return timezone.now()
    return timezone.make_aware(naive)


def parse_mpesa_message(text):
    """Return a ParsedPayment, or None if the text is not a Paybill confirmation."""
    match = MESSAGE_RE.search(str(text or ""))
    if not match:
        return None
    try:
        amount = Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation:
        return None

    payer = match.group("payer").strip()
    phone = ""
    phone_match = PHONE_IN_PAYER_RE.search(payer)
    if phone_match:
        phone = normalize_phone(phone_match.group(0)) or ""
        payer = (payer[: phone_match.start()] + " " + payer[phone_match.end():]).strip()
    name = re.sub(r"\s+", " ", payer).strip(" .")

    return ParsedPayment(
        code=match.group("code").upper(),
        amount=amount,
        payer_name=name,
        payer_phone=phone,
        account=re.sub(r"\s+", " ", match.group("account")).strip(),
        paid_at=_parse_datetime(match.group("date"), match.group("time")),
    )
