"""Finds the member a payment belongs to.

Order: payer phone, exact name, close name (needs the treasurer's confirmation).
A weak or ambiguous match is never applied automatically.
"""
import re
from dataclasses import dataclass

from django.db.models import Q

from ..models import Member, PayerAlias

PHONE = "phone"
NAME = "name"
CLOSE = "close"


@dataclass
class MatchResult:
    member: Member | None
    how: str | None  # "phone", "name", "close" or None
    ambiguous: bool = False


def name_tokens(name):
    return frozenset(t for t in re.sub(r"[^a-z\s]", " ", str(name or "").lower()).split() if len(t) > 1)


def name_key(name):
    return " ".join(sorted(name_tokens(name)))


def find_member(payer_phone, payer_name):
    members = list(Member.objects.filter(is_active=True))

    # 1. Phone number (registered phone, M-Pesa phone, or a number the treasurer linked earlier)
    if payer_phone:
        ids = {m.id for m in members if payer_phone in (m.phone, m.mpesa_phone)}
        ids |= set(
            PayerAlias.objects.filter(kind=PayerAlias.PHONE, value=payer_phone, member__is_active=True)
            .values_list("member_id", flat=True)
        )
        if len(ids) == 1:
            return MatchResult(next(m for m in members if m.id == next(iter(ids))), PHONE)
        if len(ids) > 1:
            return MatchResult(None, None, ambiguous=True)

    tokens = name_tokens(payer_name)
    if len(tokens) < 2:
        return MatchResult(None, None)

    # 2. Exact name (same words in any order), including names the treasurer linked earlier
    exact = {m.id for m in members if name_tokens(m.name) == tokens}
    key = name_key(payer_name)
    exact |= set(
        PayerAlias.objects.filter(kind=PayerAlias.NAME, value=key, member__is_active=True)
        .values_list("member_id", flat=True)
    )
    if len(exact) == 1:
        return MatchResult(next(m for m in members if m.id == next(iter(exact))), NAME)
    if len(exact) > 1:
        return MatchResult(None, None, ambiguous=True)

    # 3. Close name: at least two shared words and one name is contained in the other
    close = []
    for m in members:
        other = name_tokens(m.name)
        shared = tokens & other
        if len(shared) >= 2 and (shared == tokens or shared == other):
            close.append(m)
    if len(close) == 1:
        return MatchResult(close[0], CLOSE)
    if len(close) > 1:
        return MatchResult(None, None, ambiguous=True)

    return MatchResult(None, None)


def remember_payer(member, payer_phone, payer_name):
    """After the treasurer assigns a payment, link the payer to the member for next time."""
    if payer_phone:
        PayerAlias.objects.update_or_create(
            kind=PayerAlias.PHONE, value=payer_phone, defaults={"member": member}
        )
    key = name_key(payer_name)
    if key and len(key.split()) >= 2:
        PayerAlias.objects.update_or_create(kind=PayerAlias.NAME, value=key, defaults={"member": member})
