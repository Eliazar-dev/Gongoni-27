import math
import re
import uuid
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import IncomingMessage, Member, NotificationLog, Payment
from .services.phones import normalize_phone

PHONE_ERROR = "Enter a valid Kenyan phone number, for example 0712 345 678."


def clean_name(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    words = [w for w in value.split(" ") if w]
    if len(words) < 2:
        raise serializers.ValidationError("Please enter your full name (at least two names).")
    return value


def clean_phone(value):
    phone = normalize_phone(value)
    if not phone:
        raise serializers.ValidationError(PHONE_ERROR)
    return phone


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30)
    duration = serializers.ChoiceField(choices=[c[0] for c in Member.DURATION_CHOICES])
    mpesa_phone = serializers.CharField(max_length=30)
    website = serializers.CharField(required=False, allow_blank=True)  # hidden trap field for bots

    def validate_name(self, value):
        return clean_name(value)

    def validate_phone(self, value):
        phone = clean_phone(value)
        if Member.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return phone

    def validate_mpesa_phone(self, value):
        return clean_phone(value)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs.get("website"):
            raise serializers.ValidationError("Invalid submission.")
        attrs.pop("website", None)
        return attrs

    def create(self, validated_data):
        return Member.objects.create(**validated_data)


def percent_of(paid, target):
    paid, target = Decimal(paid or 0), Decimal(target or 0)
    if target and paid >= target:
        return 100
    return min(99, math.floor(paid / target * 100)) if target else 0


class MemberSerializer(serializers.ModelSerializer):
    paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    duration_display = serializers.CharField(source="get_duration_display", read_only=True)

    class Meta:
        model = Member
        fields = [
            "id", "code", "name", "email", "phone", "mpesa_phone", "duration", "duration_display",
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
        fields = ["name", "email", "phone", "mpesa_phone", "duration", "target", "is_active"]

    def validate_name(self, value):
        return clean_name(value)

    def validate_phone(self, value):
        phone = clean_phone(value)
        if Member.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Another member already uses this phone number.")
        return phone

    def validate_mpesa_phone(self, value):
        return clean_phone(value)

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
    suggested_member = MemberBriefSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "receipt_no", "mpesa_code", "amount", "payer_name", "payer_phone", "account_text",
            "paid_at", "status", "status_display", "source", "member", "suggested_member", "note", "created_at",
        ]


class ManualPaymentSerializer(serializers.Serializer):
    member_id = serializers.PrimaryKeyRelatedField(queryset=Member.objects.filter(is_active=True), source="member")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    mpesa_code = serializers.CharField(required=False, allow_blank=True, max_length=24)
    paid_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_mpesa_code(self, value):
        value = value.strip().upper()
        if value and Payment.objects.filter(mpesa_code=value).exists():
            raise serializers.ValidationError("A payment with this M-Pesa code already exists.")
        return value

    def create(self, validated_data):
        code = validated_data.get("mpesa_code") or f"MANUAL-{uuid.uuid4().hex[:8].upper()}"
        member = validated_data["member"]
        return Payment.objects.create(
            mpesa_code=code,
            amount=validated_data["amount"],
            payer_name=member.name,
            payer_phone=member.mpesa_phone,
            account_text="Entered by treasurer",
            paid_at=validated_data.get("paid_at") or timezone.now(),
            member=member,
            status=Payment.RECORDED,
            source="manual",
            note=validated_data.get("note", ""),
        )


class IncomingMessageSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = IncomingMessage
        fields = ["id", "sender", "status", "status_display", "detail", "text", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ["id", "kind", "channel", "status", "error", "created_at"]
