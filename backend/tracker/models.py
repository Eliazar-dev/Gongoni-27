from decimal import Decimal

from django.conf import settings
from django.db import models


def default_target():
    return Decimal(settings.TARGET_AMOUNT)


class Member(models.Model):
    DURATION_CHOICES = [("1wk", "1 week"), ("2wks", "2 weeks")]

    code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=12, unique=True, help_text="Format 2547XXXXXXXX")
    mpesa_phone = models.CharField(max_length=12, help_text="Number the member pays from, 2547XXXXXXXX")
    duration = models.CharField(max_length=4, choices=DURATION_CHOICES)
    target = models.DecimalField(max_digits=10, decimal_places=2, default=default_target)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"GN-{self.pk:04d}"
            super().save(update_fields=["code"])

    @property
    def first_name(self):
        return self.name.split()[0].title() if self.name.split() else self.name


class Payment(models.Model):
    RECORDED = "recorded"
    REVIEW = "review"
    UNASSIGNED = "unassigned"
    REVERSED = "reversed"
    STATUS_CHOICES = [
        (RECORDED, "Recorded"),
        (REVIEW, "Needs confirmation"),
        (UNASSIGNED, "Unassigned"),
        (REVERSED, "Reversed"),
    ]
    SOURCE_CHOICES = [("sms", "M-Pesa message"), ("manual", "Entered by treasurer")]

    mpesa_code = models.CharField(max_length=24, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payer_name = models.CharField(max_length=160, blank=True)
    payer_phone = models.CharField(max_length=16, blank=True)
    account_text = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField()
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.PROTECT, related_name="payments")
    suggested_member = models.ForeignKey(
        Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="suggested_payments"
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=UNASSIGNED)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default="sms")
    receipt_no = models.CharField(max_length=14, unique=True, null=True, blank=True)
    note = models.TextField(blank=True)
    raw_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at", "-id"]

    def __str__(self):
        return f"{self.mpesa_code} {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_no:
            self.receipt_no = f"RC-{self.pk:05d}"
            super().save(update_fields=["receipt_no"])


class PayerAlias(models.Model):
    """A payer number or name the treasurer has linked to a member, so it matches next time."""

    PHONE = "phone"
    NAME = "name"
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="aliases")
    kind = models.CharField(max_length=5, choices=[(PHONE, "Phone"), (NAME, "Name")])
    value = models.CharField(max_length=160)

    class Meta:
        unique_together = [("kind", "value")]

    def __str__(self):
        return f"{self.kind}:{self.value} -> {self.member_id}"


class IncomingMessage(models.Model):
    """Log of every message the phone forwards. Text is kept only for messages we could not read."""

    STATUS_CHOICES = [
        ("ignored", "Ignored (other sender)"),
        ("not_mission", "Not a mission payment"),
        ("unparsed", "Could not read"),
        ("duplicate", "Duplicate"),
        ("recorded", "Recorded"),
        ("review", "Needs confirmation"),
        ("unassigned", "Unassigned"),
    ]
    sender = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    detail = models.CharField(max_length=160, blank=True)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class NotificationLog(models.Model):
    CHANNELS = [("email", "Email"), ("sms", "SMS")]
    STATUSES = [("sent", "Sent"), ("failed", "Failed"), ("skipped", "Skipped")]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="notifications")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    kind = models.CharField(max_length=12)
    channel = models.CharField(max_length=5, choices=CHANNELS)
    status = models.CharField(max_length=8, choices=STATUSES)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
