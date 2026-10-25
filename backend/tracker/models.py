from decimal import Decimal

from django.conf import settings
from django.db import models


def default_target():
    return Decimal(settings.TARGET_AMOUNT)


class Member(models.Model):
    DURATION_CHOICES = [("1wk", "1 week"), ("2wks", "2 weeks")]

    code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=12, unique=True, help_text="Format 2547XXXXXXXX")
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
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REVERSED = "reversed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Paid"),
        (FAILED, "Failed"),
        (REVERSED, "Reversed"),
    ]
    SOURCE_CHOICES = [("paystack", "Paystack"), ("manual", "Entered by treasurer")]

    reference = models.CharField(max_length=40, unique=True)
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default="paystack")
    channel = models.CharField(max_length=30, blank=True, help_text="Paystack channel, e.g. mobile_money, card")
    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_no = models.CharField(max_length=14, unique=True, null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.reference} {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_no:
            self.receipt_no = f"RC-{self.pk:05d}"
            super().save(update_fields=["receipt_no"])
