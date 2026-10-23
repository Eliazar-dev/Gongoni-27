import hmac
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import IncomingMessage, Member, Payment
from .serializers import (
    IncomingMessageSerializer, ManualPaymentSerializer, MemberSerializer, MemberUpdateSerializer,
    NotificationSerializer, PaymentSerializer, RegisterSerializer,
)
from .services.ingest import process_incoming
from .services.matching import remember_payer
from .services.notify import dispatch, notify_payment, notify_welcome
from .services.phones import normalize_phone


class Pager(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def members_with_totals():
    paid = Coalesce(
        Sum("payments__amount", filter=Q(payments__status=Payment.RECORDED)),
        Value(Decimal("0")),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    return Member.objects.annotate(paid=paid)


# --------------------------------------------------------------------------- public


class ConfigView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "mission_name": settings.MISSION_NAME,
            "target": settings.TARGET_AMOUNT,
            "paybill": settings.PAYBILL,
            "account_text": settings.ACCOUNT_TEXT,
        })


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            member = serializer.save()
            dispatch(notify_welcome, member.pk)
        return Response({"name": member.name, "code": member.code}, status=status.HTTP_201_CREATED)


def _secret_ok(request):
    expected = settings.WEBHOOK_SECRET
    if not expected:
        return False
    given = (
        request.query_params.get("key")
        or request.headers.get("X-Webhook-Secret")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return hmac.compare_digest(str(given or ""), expected)


class WebhookView(APIView):
    """The forwarder app on the treasurer's phone posts every M-Pesa message here."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not _secret_ok(request):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        sender = data.get("from") or data.get("sender") or ""
        text = data.get("text") or data.get("message") or ""
        result = process_incoming(sender, text)
        # Always 200 for a message we understood or deliberately skipped, so the app does not retry it.
        return Response({"status": result})


# --------------------------------------------------------------------------- auth


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        user = authenticate(username=request.data.get("username", ""), password=request.data.get("password", ""))
        if not user or not user.is_staff:
            return Response({"detail": "Wrong username or password."}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.get_username()})


class MeView(APIView):
    def get(self, request):
        return Response({"username": request.user.get_username()})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- dashboard


class DashboardView(APIView):
    def get(self, request):
        active = members_with_totals().filter(is_active=True)
        count = active.count()
        target_total = active.aggregate(t=Sum("target"))["t"] or Decimal("0")
        raised = (
            Payment.objects.filter(status=Payment.RECORDED, member__is_active=True).aggregate(s=Sum("amount"))["s"]
            or Decimal("0")
        )
        completed = active.filter(paid__gte=F("target")).count()
        unpaid = active.filter(paid=0).count()
        by_duration = {row["duration"]: row["n"] for row in active.values("duration").annotate(n=Count("id"))}

        today = timezone.localdate()
        start = today - timedelta(days=13)
        rows = (
            Payment.objects.filter(status=Payment.RECORDED, paid_at__date__gte=start)
            .annotate(day=TruncDate("paid_at"))
            .values("day")
            .annotate(total=Sum("amount"))
        )
        totals = {row["day"]: row["total"] for row in rows}
        daily = [
            {"date": (start + timedelta(days=i)).isoformat(), "total": totals.get(start + timedelta(days=i), 0)}
            for i in range(14)
        ]
        recent = Payment.objects.filter(status=Payment.RECORDED).select_related("member")[:8]
        return Response({
            "members": count,
            "target_total": target_total,
            "raised": raised,
            "percent": int(min(100, raised / target_total * 100)) if target_total else 0,
            "completed": completed,
            "unpaid": unpaid,
            "in_progress": count - completed - unpaid,
            "by_duration": {"1wk": by_duration.get("1wk", 0), "2wks": by_duration.get("2wks", 0)},
            "unassigned": Payment.objects.filter(status=Payment.UNASSIGNED).count(),
            "review": Payment.objects.filter(status=Payment.REVIEW).count(),
            "unparsed": IncomingMessage.objects.filter(status="unparsed").count(),
            "daily": daily,
            "recent": PaymentSerializer(recent, many=True).data,
        })


# --------------------------------------------------------------------------- members


class MemberListView(APIView):
    def get(self, request):
        qs = members_with_totals()
        params = request.query_params

        search = params.get("q", "").strip()
        if search:
            cond = (
                Q(name__icontains=search) | Q(email__icontains=search) | Q(code__icontains=search)
                | Q(phone__icontains=search) | Q(mpesa_phone__icontains=search)
            )
            phone = normalize_phone(search)
            if phone:
                cond |= Q(phone=phone) | Q(mpesa_phone=phone)
            qs = qs.filter(cond)

        state = params.get("status")
        if state == "completed":
            qs = qs.filter(paid__gte=F("target"))
        elif state == "unpaid":
            qs = qs.filter(paid=0)
        elif state == "in_progress":
            qs = qs.filter(paid__gt=0, paid__lt=F("target"))

        if params.get("duration") in ("1wk", "2wks"):
            qs = qs.filter(duration=params["duration"])
        if params.get("active") != "all":
            qs = qs.filter(is_active=True)

        ordering = params.get("ordering", "-created_at")
        if ordering not in ("name", "-name", "paid", "-paid", "created_at", "-created_at"):
            ordering = "-created_at"
        qs = qs.order_by(ordering, "id")

        pager = Pager()
        page = pager.paginate_queryset(qs, request)
        return pager.get_paginated_response(MemberSerializer(page, many=True).data)


class MemberDetailView(APIView):
    def _get(self, pk):
        return get_object_or_404(members_with_totals(), pk=pk)

    def _payload(self, member):
        data = MemberSerializer(member).data
        data["payments"] = PaymentSerializer(member.payments.select_related("member")[:50], many=True).data
        data["notifications"] = NotificationSerializer(member.notifications.all()[:10], many=True).data
        return data

    def get(self, request, pk):
        return Response(self._payload(self._get(pk)))

    def patch(self, request, pk):
        member = self._get(pk)
        serializer = MemberUpdateSerializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(self._get(pk)))


# --------------------------------------------------------------------------- payments


class PaymentListView(APIView):
    def get(self, request):
        qs = Payment.objects.select_related("member", "suggested_member")
        params = request.query_params
        state = params.get("status", "")
        if state == "attention":
            qs = qs.filter(status__in=[Payment.REVIEW, Payment.UNASSIGNED])
        elif state:
            qs = qs.filter(status__in=state.split(","))
        search = params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(mpesa_code__icontains=search) | Q(payer_name__icontains=search) | Q(payer_phone__icontains=search)
                | Q(member__name__icontains=search) | Q(receipt_no__icontains=search)
            )
        pager = Pager()
        page = pager.paginate_queryset(qs, request)
        return pager.get_paginated_response(PaymentSerializer(page, many=True).data)

    def post(self, request):
        """Treasurer records a payment by hand (for example a missed message)."""
        serializer = ManualPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            payment = serializer.save()
            dispatch(notify_payment, payment.pk)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentAssignView(APIView):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status == Payment.REVERSED:
            return Response({"detail": "This payment was reversed."}, status=status.HTTP_400_BAD_REQUEST)
        member = get_object_or_404(Member, pk=request.data.get("member_id") or 0, is_active=True)
        if payment.status == Payment.RECORDED and payment.member_id == member.id:
            return Response({"detail": "Already assigned to this member."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            payment.member = member
            payment.suggested_member = None
            payment.status = Payment.RECORDED
            payment.save()
            if request.data.get("remember", True):
                remember_payer(member, payment.payer_phone, payment.payer_name)
            dispatch(notify_payment, payment.pk)
        return Response(PaymentSerializer(payment).data)


class PaymentReverseView(APIView):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status == Payment.REVERSED:
            return Response({"detail": "Already reversed."}, status=status.HTTP_400_BAD_REQUEST)
        note = str(request.data.get("note", "")).strip()
        payment.status = Payment.REVERSED
        payment.note = (payment.note + "\n" if payment.note else "") + f"Reversed: {note or 'no reason given'}"
        payment.save()
        return Response(PaymentSerializer(payment).data)


class PaymentResendView(APIView):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status != Payment.RECORDED or not payment.member_id:
            return Response({"detail": "Only recorded payments can be resent."}, status=status.HTTP_400_BAD_REQUEST)
        dispatch(notify_payment, payment.pk)
        return Response({"detail": "Message queued."})


class IncomingListView(APIView):
    def get(self, request):
        qs = IncomingMessage.objects.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        pager = Pager()
        page = pager.paginate_queryset(qs, request)
        return pager.get_paginated_response(IncomingMessageSerializer(page, many=True).data)


# --------------------------------------------------------------------------- export


class ExportView(APIView):
    def get(self, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        wb = Workbook()
        members_sheet = wb.active
        members_sheet.title = "Members"
        members_sheet.append([
            "Code", "Name", "Phone", "Email", "M-Pesa number", "Duration", "Target (KES)", "Paid (KES)",
            "Balance (KES)", "Percent", "Status", "Registered",
        ])
        for m in members_with_totals().filter(is_active=True).order_by("name"):
            data = MemberSerializer(m).data
            members_sheet.append([
                m.code, m.name, m.phone, m.email, m.mpesa_phone, m.get_duration_display(), float(m.target),
                float(data["paid"]), float(data["balance"]), data["percent"] / 100, data["status"].replace("_", " "),
                timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M"),
            ])
        for row in members_sheet.iter_rows(min_row=2, min_col=10, max_col=10):
            for cell in row:
                cell.number_format = "0%"

        pay_sheet = wb.create_sheet("Payments")
        pay_sheet.append(["Receipt", "M-Pesa code", "Date", "Amount (KES)", "Payer", "Payer phone", "Member", "Status", "Source"])
        for p in Payment.objects.select_related("member"):
            pay_sheet.append([
                p.receipt_no, p.mpesa_code, timezone.localtime(p.paid_at).strftime("%Y-%m-%d %H:%M"), float(p.amount),
                p.payer_name, p.payer_phone, p.member.name if p.member else "", p.get_status_display(), p.get_source_display(),
            ])

        header_fill = PatternFill("solid", fgColor="0E4568")
        for sheet in (members_sheet, pay_sheet):
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = header_fill
            for column in sheet.columns:
                width = max(len(str(c.value or "")) for c in column) + 2
                sheet.column_dimensions[column[0].column_letter].width = min(max(width, 10), 40)
            sheet.freeze_panes = "A2"

        buffer = BytesIO()
        wb.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="gongoni27-{timezone.localdate():%Y%m%d}.xlsx"'
        return response
