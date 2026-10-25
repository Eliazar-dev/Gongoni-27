"""Welcome, receipt and payment request emails."""
import math
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Payment


def kes(value):
    value = Decimal(value)
    return f"{value:,.0f}" if value == value.to_integral() else f"{value:,.2f}"


def percent_of(paid, target):
    paid, target = Decimal(paid or 0), Decimal(target or 0)
    if target and paid >= target:
        return 100
    return min(99, math.floor(paid / target * 100)) if target else 0


def member_progress(member):
    """Totals counted only from successful payments."""
    paid = member.payments.filter(status=Payment.SUCCESS).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    target = Decimal(member.target)
    return {
        "paid": paid,
        "target": target,
        "balance": max(target - paid, Decimal("0")),
        "percent": percent_of(paid, target),
        "completed": paid >= target,
    }


def build_receipt(payment):
    member = payment.member
    p = member_progress(member)
    mission = settings.MISSION_NAME
    lines = [
        f"Dear {member.first_name},",
        "",
        f"We have received your payment for {mission}. Thank you!",
        "",
        f"Receipt number: {payment.receipt_no}",
        f"Reference:      {payment.reference}",
        f"Date:           {timezone.localtime(payment.paid_at or payment.created_at):%d %b %Y, %I:%M %p}",
        f"Amount paid:    KES {kes(payment.amount)}",
        "",
        f"Total paid so far: KES {kes(p['paid'])} of KES {kes(p['target'])} ({p['percent']}%)",
        f"Balance remaining: KES {kes(p['balance'])}",
        "",
        "Congratulations! You have completed your mission target. God bless you."
        if p["completed"] else "You can pay the balance in as many instalments as you like.",
        "",
        mission,
    ]
    subject = f"{mission}: target completed, thank you!" if p["completed"] else f"{mission}: KES {kes(payment.amount)} received"
    return subject, "\n".join(lines)


def _send(subject, text, template, context, to):
    """Send a plain-text email with an HTML version attached."""
    context = {"subject": subject, "mission": settings.MISSION_NAME, **context}
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    message.attach_alternative(render_to_string(template, context), "text/html")
    message.send(fail_silently=True)


def send_receipt(payment):
    subject, body = build_receipt(payment)
    p = member_progress(payment.member)
    _send(subject, body, "tracker/emails/receipt.html", {
        "payment": payment,
        "member": payment.member,
        "progress": p,
        "amount": kes(payment.amount),
        "paid": kes(p["paid"]),
        "target": kes(p["target"]),
        "balance": kes(p["balance"]),
        "paid_on": f"{timezone.localtime(payment.paid_at or payment.created_at):%d %b %Y, %I:%M %p}",
        "channel": payment.channel.replace("_", " ").title(),
    }, payment.member.email)


def send_welcome(member):
    mission = settings.MISSION_NAME
    body = (
        f"Dear {member.first_name},\n\nThank you for registering for {mission}.\n\n"
        f"Your target is KES {kes(member.target)}. You can pay online in as many instalments as you like, "
        "and you will get a receipt with your balance after every payment.\n\n"
        f"Your member code: {member.code}\n\n{mission}"
    )
    _send(f"Welcome to {mission}", body, "tracker/emails/welcome.html",
          {"member": member, "target": kes(member.target)}, member.email)


def send_payment_request(payment, pay_url, message=""):
    member = payment.member
    p = member_progress(member)
    mission = settings.MISSION_NAME
    subject = f"{mission}: please pay KES {kes(payment.amount)}"
    text = (
        f"Dear {member.first_name},\n\n"
        f"This is a request to pay KES {kes(payment.amount)} toward your {mission} commitment.\n\n"
        + (f"{message}\n\n" if message else "")
        + f"Pay securely here: {pay_url}\n\n"
        f"Paid so far: KES {kes(p['paid'])} of KES {kes(p['target'])} ({p['percent']}%)\n"
        f"Balance: KES {kes(p['balance'])}\n\n{mission}"
    )
    _send(subject, text, "tracker/emails/payment_request.html", {
        "member": member,
        "amount": kes(payment.amount),
        "pay_url": pay_url,
        "message": message,
        "progress": p,
        "paid": kes(p["paid"]),
        "target": kes(p["target"]),
        "balance": kes(p["balance"]),
    }, member.email)
