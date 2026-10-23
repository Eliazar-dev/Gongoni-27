"""SMS sending. 'console' prints the message (testing), 'africastalking' really sends it."""
import logging

import requests
from django.conf import settings

from .phones import to_international

logger = logging.getLogger(__name__)

AT_LIVE_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


def send_sms(phone, message):
    """Return (ok, error_text)."""
    if not phone:
        return False, "No phone number"
    if settings.SMS_BACKEND == "africastalking":
        return _send_africastalking(to_international(phone), message)
    logger.info("[SMS to %s] %s", phone, message)
    return True, ""


def _send_africastalking(to, message):
    if not settings.AT_API_KEY:
        return False, "AT_API_KEY is not set"
    url = AT_SANDBOX_URL if settings.AT_USERNAME == "sandbox" else AT_LIVE_URL
    data = {"username": settings.AT_USERNAME, "to": to, "message": message}
    if settings.AT_SENDER_ID:
        data["from"] = settings.AT_SENDER_ID
    try:
        response = requests.post(
            url,
            data=data,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        recipients = response.json().get("SMSMessageData", {}).get("Recipients", [])
        if recipients and str(recipients[0].get("status", "")).lower() == "success":
            return True, ""
        status = recipients[0].get("status") if recipients else "no recipient in response"
        return False, f"Provider said: {status}"
    except Exception as exc:  # network problems must never crash payment recording
        logger.exception("SMS failed")
        return False, str(exc)[:300]
