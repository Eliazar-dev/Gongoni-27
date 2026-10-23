"""Email first, then SMS, with receipt, percentage paid and balance."""
import logging
import math
import threading
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import connections, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import escape

from ..models import Member, NotificationLog, Payment
from .sms import send_sms

logger = logging.getLogger(__name__)


def kes(value):
    value = Decimal(value)
    return f"{value:,.0f}" if value == value.to_integral() else f"{value:,.2f}"


def member_progress(member):
    """Totals counted only from recorded (not reversed or unassigned) payments."""
    paid = member.payments.filter(status=Payment.RECORDED).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    target = Decimal(member.target)
    balance = max(target - paid, Decimal("0"))
    completed = paid >= target
    percent = 100 if completed else min(99, math.floor(paid / target * 100)) if target else 0
    return {"paid": paid, "target": target, "balance": balance, "percent": percent, "completed": completed}


def build_receipt(payment, member):
    p = member_progress(member)
    first = member.first_name
    mission = settings.MISSION_NAME
    lines = [
        f"Dear {first},",
        "",
        f"We have received your payment for {mission}. Thank you!",
        "",
        f"Receipt number: {payment.receipt_no}",
        f"M-Pesa code:    {payment.mpesa_code}",
        f"Date:           {timezone.localtime(payment.paid_at).strftime('%d %b %Y, %I:%M %p')}",
        f"Amount paid:    KES {kes(payment.amount)}",
        "",
        f"Total paid so far: KES {kes(p['paid'])} of KES {kes(p['target'])} ({p['percent']}%)",
        f"Balance remaining: KES {kes(p['balance'])}",
        "",
    ]
    if p["completed"]:
        lines.append("Congratulations! You have completed your mission target. God bless you.")
    else:
        lines.append(
            f"To continue, pay to Paybill {settings.PAYBILL}, account number: {settings.ACCOUNT_TEXT}."
        )
    lines += ["", f"{mission}", "Seventh-day Adventist Church, Mount Kenya University"]
    text = "\n".join(lines)

    bar = p["percent"]
    html = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:auto;color:#0F2A3D">
<div style="background:#0E4568;color:#fff;padding:18px 22px;border-radius:12px 12px 0 0">
<div style="font-size:13px;letter-spacing:2px;opacity:.85">{escape(mission.upper())}</div>
<div style="font-size:22px;font-weight:bold">Payment received</div></div>
<div style="border:1px solid #D5E3EC;border-top:0;padding:22px;border-radius:0 0 12px 12px">
<p>Dear {escape(first)}, thank you! Here is your receipt.</p>
<table style="width:100%;border-collapse:collapse;font-size:15px">
<tr><td style="padding:6px 0;color:#5C7384">Receipt number</td><td style="text-align:right"><b>{escape(payment.receipt_no)}</b></td></tr>
<tr><td style="padding:6px 0;color:#5C7384">M-Pesa code</td><td style="text-align:right">{escape(payment.mpesa_code)}</td></tr>
<tr><td style="padding:6px 0;color:#5C7384">Amount paid</td><td style="text-align:right"><b>KES {kes(payment.amount)}</b></td></tr>
</table>
<div style="margin-top:18px;font-size:14px;color:#5C7384">Your progress</div>
<div style="background:#E3EEF5;border-radius:10px;height:14px;overflow:hidden;margin:6px 0"><div style="background:#F2B230;width:{bar}%;height:14px"></div></div>
<div style="font-size:15px"><b>{p['percent']}%</b> paid &middot; KES {kes(p['paid'])} of KES {kes(p['target'])}<br>Balance: <b>KES {kes(p['balance'])}</b></div>
<p style="margin-top:18px;font-size:14px">{"Congratulations! You have completed your mission target. God bless you." if p["completed"] else f"To continue, pay to Paybill <b>{escape(settings.PAYBILL)}</b>, account number <b>{escape(settings.ACCOUNT_TEXT)}</b>."}</p>
</div></div>"""

    if p["completed"]:
        sms = (
            f"Congratulations {first}! Your KES {kes(p['target'])} {mission} target is complete. "
            f"Received KES {kes(payment.amount)}. Receipt {payment.receipt_no}. God bless you!"
        )
        subject = f"{mission}: target completed, thank you!"
    else:
        sms = (
            f"Dear {first}, we received KES {kes(payment.amount)}. Total KES {kes(p['paid'])} "
            f"({p['percent']}% of {kes(p['target'])}). Balance KES {kes(p['balance'])}. "
            f"Receipt {payment.receipt_no}. Thank you for giving to {mission}."
        )
        subject = f"{mission}: payment received, KES {kes(payment.amount)}"
    return {"subject": subject, "text": text, "html": html, "sms": sms, "completed": p["completed"]}


def _send_email(member, subject, text, html, kind, payment=None):
    if not member.email:
        NotificationLog.objects.create(member=member, payment=payment, kind=kind, channel="email", status="skipped", error="No email")
        return
    try:
        message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [member.email])
        message.attach_alternative(html, "text/html")
        message.send()
        NotificationLog.objects.create(member=member, payment=payment, kind=kind, channel="email", status="sent")
    except Exception as exc:
        logger.exception("Email failed")
        NotificationLog.objects.create(member=member, payment=payment, kind=kind, channel="email", status="failed", error=str(exc)[:300])


def _send_sms(member, text, kind, payment=None):
    ok, error = send_sms(member.phone, text)
    NotificationLog.objects.create(
        member=member, payment=payment, kind=kind, channel="sms", status="sent" if ok else "failed", error=error
    )


def notify_payment(payment_id):
    """Email first, then SMS. Safe to call from a background thread."""
    try:
        payment = Payment.objects.select_related("member").get(pk=payment_id)
        member = payment.member
        if not member or payment.status != Payment.RECORDED:
            return
        receipt = build_receipt(payment, member)
        kind = "completed" if receipt["completed"] else "receipt"
        _send_email(member, receipt["subject"], receipt["text"], receipt["html"], kind, payment)
        _send_sms(member, receipt["sms"], kind, payment)
    except Exception:
        logger.exception("notify_payment failed")


def notify_welcome(member_id):
    try:
        member = Member.objects.get(pk=member_id)
        mission = settings.MISSION_NAME
        text = (
            f"Dear {member.first_name},\n\nThank you for registering for {mission}. See you soon!\n\n"
            f"Your target is KES {kes(member.target)}. You can pay in as many instalments as you like:\n"
            f"  Paybill: {settings.PAYBILL}\n  Account number: {settings.ACCOUNT_TEXT}\n\n"
            "After every payment you will get a message with your receipt, the percentage paid and your balance.\n\n"
            f"{mission}\nSeventh-day Adventist Church, Mount Kenya University"
        )
        html = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:auto;color:#0F2A3D">
<div style="background:#0E4568;color:#fff;padding:18px 22px;border-radius:12px 12px 0 0"><div style="font-size:22px;font-weight:bold">Welcome, {escape(member.first_name)}!</div></div>
<div style="border:1px solid #D5E3EC;border-top:0;padding:22px;border-radius:0 0 12px 12px">
<p>Thank you for registering for <b>{escape(mission)}</b>. See you soon!</p>
<p>Your target is <b>KES {kes(member.target)}</b>. You can pay in as many instalments as you like:</p>
<p style="background:#EAF5FB;padding:12px 16px;border-radius:10px">Paybill: <b>{escape(settings.PAYBILL)}</b><br>Account number: <b>{escape(settings.ACCOUNT_TEXT)}</b></p>
<p>After every payment you will get a message with your receipt, the percentage paid and your balance.</p></div></div>"""
        _send_email(member, f"Welcome to {mission}", text, html, "welcome")
        if settings.SEND_WELCOME_SMS:
            _send_sms(
                member,
                f"Welcome {member.first_name}! You are registered for {mission}. Target KES {kes(member.target)}. "
                f"Paybill {settings.PAYBILL}, account: {settings.ACCOUNT_TEXT}.",
                "welcome",
            )
    except Exception:
        logger.exception("notify_welcome failed")


def _run_in_thread(fn, args):
    try:
        fn(*args)
    finally:
        connections.close_all()  # this thread's own database connections


def dispatch(fn, *args):
    """Send in the background after the save is committed (NOTIFY_ASYNC on), or right away (off, for tests)."""
    if settings.NOTIFY_ASYNC:
        transaction.on_commit(lambda: threading.Thread(target=_run_in_thread, args=(fn, args), daemon=True).start())
    else:
        fn(*args)
