import re


def normalize_phone(raw):
    """Return a Kenyan number as 2547XXXXXXXX / 2541XXXXXXXX, or None if it is not valid."""
    value = re.sub(r"[\s\-().]", "", str(raw or ""))
    if value.startswith("+"):
        value = value[1:]
    if re.fullmatch(r"0[17]\d{8}", value):
        return "254" + value[1:]
    if re.fullmatch(r"[17]\d{8}", value):
        return "254" + value
    if re.fullmatch(r"254[17]\d{8}", value):
        return value
    return None


def to_international(phone):
    """254712345678 -> +254712345678 (what SMS providers expect)."""
    return "+" + phone if phone and not phone.startswith("+") else phone
