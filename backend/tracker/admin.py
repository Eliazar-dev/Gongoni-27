from django.contrib import admin

from .models import Member, Payment


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "phone", "email", "duration", "target", "is_active", "created_at")
    search_fields = ("name", "phone", "email", "code")
    list_filter = ("duration", "is_active")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "reference", "amount", "member", "status", "source", "paid_at")
    search_fields = ("reference", "receipt_no", "member__name")
    list_filter = ("status", "source")
