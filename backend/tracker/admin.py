from django.contrib import admin

from .models import IncomingMessage, Member, NotificationLog, PayerAlias, Payment


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "phone", "mpesa_phone", "duration", "target", "is_active", "created_at")
    search_fields = ("name", "phone", "email", "code")
    list_filter = ("duration", "is_active")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "mpesa_code", "amount", "payer_name", "member", "status", "paid_at")
    search_fields = ("mpesa_code", "payer_name", "payer_phone", "receipt_no")
    list_filter = ("status", "source")


admin.site.register(PayerAlias)
admin.site.register(IncomingMessage)
admin.site.register(NotificationLog)
