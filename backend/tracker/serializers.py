import re
import uuid
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .emails import percent_of
from .models import Member, Payment

PHONE_ERROR = "Enter a valid Kenyan phone number, for example 0712 345 678."


def normalize_phone(raw):
    """Return a Kenyan number as 2547XXXXXXXX / 2541XXXXXXXX, or None if it is not valid."""
    value = re.sub(r"[\s\-().]", "", str(raw or "")).removeprefix("+")
    if re.fullmatch(r"0[17]\d{8}", value):
        return "254" + value[1:]
    if re.fullmatch(r"[17]\d{8}", value):
        return "254" + value
    if re.fullmatch(r"254[17]\d{8}", value):
        return value
    return None


def clean_name(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(value.split(" ")) < 2:
        raise serializers.ValidationError("Please enter your full name (at least two names).")
    return value


def clean_phone(value):
    phone = normalize_phone(value)
    if not phone:
        raise serializers.ValidationError(PHONE_ERROR)
    return phone


def clean_email(value, exclude_pk=None):
    email = value.strip().lower()
    taken = Member.objects.filter(email__iexact=email)
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise serializers.ValidationError("This email is already registered. Use Track progress to sign in.")
    return email


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30)
    duration = serializers.ChoiceField(choices=[c[0] for c in Member.DURATION_CHOICES])
    website = serializers.CharField(required=False, allow_blank=True)  # hidden trap field for bots

    def validate_name(self, value):
        return clean_name(value)

    def validate_phone(self, value):
        phone = clean_phone(value)
        if Member.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return phone

    def validate_email(self, value):
        return clean_email(value)

    def validate(self, attrs):
        if attrs.pop("website", None):
            raise serializers.ValidationError("Invalid submission.")
        return attrs

    def create(self, validated_data):
        return Member.objects.create(**validated_data)


class PayStartSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=30)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("10"))

    def validate_phone(self, value):
        member = Member.objects.filter(phone=clean_phone(value), is_active=True).first()
        if not member:
            raise serializers.ValidationError("No registered member uses this phone number.")
        return member


class MemberSerializer(serializers.ModelSerializer):
    paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    duration_display = serializers.CharField(source="get_duration_display", read_only=True)

    class Meta:
        model = Member
        fields = [
            "id", "code", "name", "email", "phone", "duration", "duration_display",
            "target", "paid", "balance", "percent", "status", "is_active", "created_at",
        ]

    def _paid(self, obj):
        return Decimal(getattr(obj, "paid", 0) or 0)

    def get_paid(self, obj):
        return self._paid(obj)

    def get_balance(self, obj):
        return max(Decimal(obj.target) - self._paid(obj), Decimal("0"))

    def get_percent(self, obj):
        return percent_of(self._paid(obj), obj.target)

    def get_status(self, obj):
        paid = self._paid(obj)
        if paid >= Decimal(obj.target):
            return "completed"
        return "in_progress" if paid > 0 else "unpaid"


class MemberUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["name", "email", "phone", "duration", "target", "is_active"]

    def validate_name(self, value):
        return clean_name(value)

    def validate_email(self, value):
        return clean_email(value, exclude_pk=self.instance.pk)

    def validate_phone(self, value):
        phone = clean_phone(value)
        if Member.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Another member already uses this phone number.")
        return phone

    def validate_target(self, value):
        if value <= 0:
            raise serializers.ValidationError("Target must be more than zero.")
        return value


class MemberBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "code", "name", "phone"]


class PaymentSerializer(serializers.ModelSerializer):
    member = MemberBriefSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "receipt_no", "reference", "amount", "status", "status_display", "source", "channel",
            "member", "paid_at", "note", "created_at",
        ]


class ManualPaymentSerializer(serializers.Serializer):
    """Treasurer records a payment made outside Paystack, e.g. cash."""

    member_id = serializers.PrimaryKeyRelatedField(queryset=Member.objects.filter(is_active=True), source="member")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    paid_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return Payment.objects.create(
            reference=f"MANUAL-{uuid.uuid4().hex[:8].upper()}",
            member=validated_data["member"],
            amount=validated_data["amount"],
            paid_at=validated_data.get("paid_at") or timezone.now(),
            status=Payment.SUCCESS,
            source="manual",
            note=validated_data.get("note", ""),
        )


class PaymentRequestSerializer(serializers.Serializer):
    """Admin asks a member to pay: an email with a checkout link, and optionally an M-Pesa prompt."""

    member_id = serializers.PrimaryKeyRelatedField(queryset=Member.objects.filter(is_active=True), source="member")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("10"))
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)
    mpesa = serializers.BooleanField(required=False, default=False)
