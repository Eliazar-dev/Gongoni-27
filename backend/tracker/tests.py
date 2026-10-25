import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .emails import build_receipt, member_progress
from .models import Member, Payment
from .serializers import normalize_phone

SECRET = "sk_test_secret"


def make_member(name="Belinda Boyani Mayore", phone="254707548406", email="belinda@example.org", **kw):
    return Member.objects.create(name=name, phone=phone, email=email, duration=kw.pop("duration", "2wks"), **kw)


def pay(member, amount, ref, status="success"):
    return Payment.objects.create(reference=ref, amount=Decimal(amount), paid_at=timezone.now(), member=member, status=status)


def paystack_tx(payment, status="success", amount=None, currency="KES"):
    return {
        "reference": payment.reference,
        "status": status,
        "amount": int(payment.amount * 100) if amount is None else amount,
        "currency": currency,
        "channel": "mobile_money",
        "paid_at": "2026-10-22T09:05:00.000Z",
    }


class PhoneTests(TestCase):
    def test_formats(self):
        for raw in ["0712 345 678", "+254712345678", "254712345678", "712345678", "0112345678"]:
            self.assertIsNotNone(normalize_phone(raw), raw)
        self.assertEqual(normalize_phone("0712 345 678"), "254712345678")

    def test_invalid(self):
        for raw in ["", "12345", "0612345678", "254712", "abc", "2547123456789"]:
            self.assertIsNone(normalize_phone(raw), raw)


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.body = {"name": "Grace  wanjiru Kamau", "email": "Grace@Example.org", "phone": "0712 345 678", "duration": "2wks"}

    def test_register(self):
        response = self.client.post("/api/register/", self.body, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        member = Member.objects.get()
        self.assertEqual(
            (member.name, member.email, member.phone, member.target),
            ("Grace wanjiru Kamau", "grace@example.org", "254712345678", Decimal("3500")),
        )
        self.assertRegex(member.code, r"^GN-\d{4}$")
        self.assertEqual(len(mail.outbox), 1)

    def test_same_phone_cannot_register_twice(self):
        self.client.post("/api/register/", self.body, format="json")
        response = self.client.post("/api/register/", {**self.body, "phone": "+254712345678"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())

    def test_same_email_cannot_register_twice(self):
        self.client.post("/api/register/", self.body, format="json")
        response = self.client.post("/api/register/", {**self.body, "email": " GRACE@example.org", "phone": "0722 000 111"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.json()["email"][0])
        self.assertEqual(Member.objects.count(), 1)

    def test_bad_inputs(self):
        for field, value in [("phone", "12345"), ("email", "nope"), ("duration", "3wks"), ("name", "Madonna")]:
            response = self.client.post("/api/register/", {**self.body, field: value}, format="json")
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json())

    def test_bot_trap_field(self):
        response = self.client.post("/api/register/", {**self.body, "website": "http://spam"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Member.objects.count(), 0)


@override_settings(PAYSTACK_SECRET_KEY=SECRET, PAYSTACK_CURRENCY="KES")
class PaystackTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.member = make_member()

    @patch("tracker.paystack._call", return_value={"authorization_url": "https://checkout.paystack.com/abc"})
    def test_start_payment(self, call):
        response = self.client.post("/api/pay/", {"phone": "0707 548 406", "amount": "1000"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["authorization_url"], "https://checkout.paystack.com/abc")
        payment = Payment.objects.get()
        self.assertEqual((payment.member, payment.status, payment.amount), (self.member, "pending", Decimal("1000")))
        payload = call.call_args.kwargs["json"]
        self.assertEqual((payload["amount"], payload["email"], payload["reference"]), (100000, self.member.email, payment.reference))

    def test_unknown_phone_cannot_pay(self):
        response = self.client.post("/api/pay/", {"phone": "0799 000 111", "amount": "1000"}, format="json")
        self.assertEqual(response.status_code, 400)

    def webhook(self, body, signature=None):
        raw = json.dumps(body).encode()
        sig = signature or hmac.new(SECRET.encode(), raw, hashlib.sha512).hexdigest()
        return self.client.post("/api/paystack/webhook/", raw, content_type="application/json", HTTP_X_PAYSTACK_SIGNATURE=sig)

    def test_progress_lookup_confirms_payment_the_callback_missed(self):
        payment = pay(self.member, "500", "GN27-MISSED", status="pending")
        with patch("tracker.paystack._call", return_value=paystack_tx(payment)), \
                self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/progress/", {"email": "belinda@example.org", "phone": "0707548406"}, format="json")
        self.assertEqual(response.json()["paid"], 500)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertEqual(len(mail.outbox), 1)

    def test_sync_leaves_fresh_checkout_pending(self):
        from .paystack import sync_pending
        payment = pay(self.member, "500", "GN27-FRESH", status="pending")
        with patch("tracker.paystack._call", return_value=paystack_tx(payment, status="abandoned")):
            sync_pending(Payment.objects.all())
            payment.refresh_from_db()
            self.assertEqual(payment.status, "pending")
            Payment.objects.filter(pk=payment.pk).update(created_at=timezone.now() - timezone.timedelta(hours=1))
            sync_pending(Payment.objects.all())
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    def test_webhook_marks_payment_paid_and_emails_receipt(self):
        payment = pay(self.member, "1000", "GN27-A", status="pending")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.webhook({"event": "charge.success", "data": paystack_tx(payment)})
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.channel), ("success", "mobile_money"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("KES 2,500", mail.outbox[0].body)
        html, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn(payment.receipt_no, html)

    def test_webhook_twice_counts_once(self):
        payment = pay(self.member, "1000", "GN27-A", status="pending")
        with self.captureOnCommitCallbacks(execute=True):
            self.webhook({"event": "charge.success", "data": paystack_tx(payment)})
            self.webhook({"event": "charge.success", "data": paystack_tx(payment)})
        self.assertEqual(len(mail.outbox), 1)

    def test_webhook_rejects_bad_signature(self):
        payment = pay(self.member, "1000", "GN27-A", status="pending")
        response = self.webhook({"event": "charge.success", "data": paystack_tx(payment)}, signature="bad")
        self.assertEqual(response.status_code, 401)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")

    def test_wrong_amount_is_not_accepted(self):
        payment = pay(self.member, "1000", "GN27-A", status="pending")
        self.webhook({"event": "charge.success", "data": paystack_tx(payment, amount=100)})
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    def test_verify_endpoint(self):
        payment = pay(self.member, "1000", "GN27-A", status="pending")
        with patch("tracker.paystack._call", return_value=paystack_tx(payment)):
            data = self.client.get("/api/pay/verify/GN27-A/").json()
        self.assertEqual((data["status"], data["percent"], Decimal(data["balance"])), ("success", 28, Decimal("2500")))


    def test_progress_sign_in_needs_matching_email_and_phone(self):
        pay(self.member, "1000", "P1")
        lookup = lambda email, phone: self.client.post("/api/progress/", {"email": email, "phone": phone}, format="json")
        data = lookup(" Belinda@Example.org ", "0707548406").json()
        self.assertEqual((data["first_name"], data["percent"], len(data["payments"])), ("Belinda", 28, 1))
        self.assertEqual((data["name"], data["email"], data["duration"]), ("Belinda Boyani Mayore", "belinda@example.org", "2 weeks"))
        self.assertEqual(lookup("belinda@example.org", "0799000111").status_code, 404)
        self.assertEqual(lookup("someone@else.org", "0707548406").status_code, 404)
        self.assertEqual(lookup("", "0707548406").status_code, 404)
        self.assertEqual(self.client.get("/api/progress/?phone=0707548406").status_code, 405)


class ReceiptTests(TestCase):
    def test_percentages_and_balance(self):
        member = make_member()
        payment = pay(member, "1000", "P1")
        progress = member_progress(member)
        self.assertEqual((progress["percent"], progress["balance"]), (28, Decimal("2500")))
        self.assertIn("(28%)", build_receipt(payment)[1])

    def test_never_shows_100_before_completion(self):
        member = make_member()
        pay(member, "3499", "P1")
        self.assertEqual(member_progress(member)["percent"], 99)

    def test_completion_message(self):
        member = make_member()
        pay(member, "2000", "P1")
        subject, body = build_receipt(pay(member, "1500", "P2"))
        self.assertIn("Congratulations", body)
        self.assertIn("completed", subject)

    def test_only_successful_payments_count(self):
        member = make_member()
        pay(member, "1000", "P1")
        pay(member, "500", "P2", status="reversed")
        pay(member, "500", "P3", status="pending")
        pay(member, "500", "P4", status="failed")
        self.assertEqual(member_progress(member)["paid"], Decimal("1000"))


class AdminApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("treasurer", password="pass12345", is_staff=True)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user).key)
        self.belinda = make_member()
        self.john = make_member("John Kamau Mwangi", "254711111111", email="john@example.org")

    def test_login(self):
        anon = APIClient()
        self.assertEqual(anon.post("/api/auth/login/", {"username": "treasurer", "password": "bad"}, format="json").status_code, 400)
        User.objects.create_user("member", password="pass12345")
        self.assertEqual(anon.post("/api/auth/login/", {"username": "member", "password": "pass12345"}, format="json").status_code, 400)
        ok = anon.post("/api/auth/login/", {"username": "treasurer", "password": "pass12345"}, format="json")
        self.assertTrue(ok.json()["token"])

    def test_admin_endpoints_need_a_token(self):
        anon = APIClient()
        for path in ["/api/dashboard/", "/api/members/", "/api/payments/", "/api/export/"]:
            self.assertEqual(anon.get(path).status_code, 401, path)

    def test_non_staff_token_is_refused(self):
        user = User.objects.create_user("plain", password="x12345678")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        self.assertEqual(client.get("/api/members/").status_code, 403)

    def test_payment_list_summary(self):
        pay(self.belinda, "1000", "P1")
        pay(self.john, "3500", "P2")
        pay(self.john, "200", "P3", status="failed")
        summary = self.client.get("/api/payments/?status=success").json()["summary"]
        self.assertEqual(
            {k: Decimal(str(summary[k])) for k in ("paid", "target", "balance", "shown_amount")},
            {"paid": Decimal("4500"), "target": Decimal("7000"), "balance": Decimal("2500"), "shown_amount": Decimal("4500")},
        )
        self.assertEqual(summary["shown_count"], 2)

    def test_payment_detail_includes_member_progress(self):
        payment = pay(self.belinda, "1000", "P1")
        data = self.client.get(f"/api/payments/{payment.id}/").json()
        self.assertEqual((data["reference"], data["member"]["name"], data["member"]["percent"]), ("P1", "Belinda Boyani Mayore", 28))

    def test_member_list_search_and_filters(self):
        pay(self.belinda, "30", "P1")
        rows = self.client.get("/api/members/").json()["results"]
        belinda = next(r for r in rows if r["name"] == "Belinda Boyani Mayore")
        self.assertEqual((float(belinda["paid"]), belinda["status"]), (30.0, "in_progress"))
        self.assertEqual(len(self.client.get("/api/members/?q=john").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?q=0711111111").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?status=unpaid").json()["results"]), 1)

    def test_member_edit(self):
        response = self.client.patch(f"/api/members/{self.john.id}/", {"phone": "0733 000 111"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        clash = self.client.patch(f"/api/members/{self.john.id}/", {"phone": self.belinda.phone}, format="json")
        self.assertEqual(clash.status_code, 400)

    def test_manual_payment_and_reverse(self):
        response = self.client.post("/api/payments/", {"member_id": self.john.id, "amount": "1500", "note": "cash"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        payment = Payment.objects.get()
        self.assertEqual((payment.source, payment.status), ("manual", "success"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.post(f"/api/payments/{payment.id}/reverse/", {"note": "mistake"}, format="json").status_code, 200)
        self.assertEqual(member_progress(self.john)["paid"], 0)
        self.assertEqual(self.client.post(f"/api/payments/{payment.id}/reverse/", {}, format="json").status_code, 400)

    @override_settings(PAYSTACK_SECRET_KEY=SECRET)
    def test_request_payment_emails_a_checkout_link(self):
        with patch("tracker.paystack._call", return_value={"authorization_url": "https://checkout.paystack.com/req1"}):
            response = self.client.post("/api/payments/request/", {"member_id": self.john.id, "amount": "1500", "message": "Deadline is Friday"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["emailed"], response.json()["mpesa"]), ("john@example.org", None))
        payment = Payment.objects.get()
        self.assertEqual((payment.status, payment.amount, payment.note), ("pending", Decimal("1500"), "Requested by treasurer"))
        self.assertEqual(len(mail.outbox), 1)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("https://checkout.paystack.com/req1", html)
        self.assertIn("Deadline is Friday", html)

    @override_settings(PAYSTACK_SECRET_KEY=SECRET)
    def test_request_payment_with_mpesa_prompt(self):
        def fake(method, path, **kwargs):
            if path == "/charge":
                self.assertEqual(kwargs["json"]["mobile_money"], {"phone": "+254711111111", "provider": "mpesa"})
                return {"status": "pay_offline", "display_text": "Enter your PIN"}
            return {"authorization_url": "https://checkout.paystack.com/req2"}
        with patch("tracker.paystack._call", side_effect=fake):
            data = self.client.post("/api/payments/request/", {"member_id": self.john.id, "amount": "500", "mpesa": True}, format="json").json()
        self.assertEqual(data["mpesa"], {"sent": True, "detail": "Enter your PIN"})
        self.assertEqual(Payment.objects.filter(status="pending").count(), 2)

    @override_settings(PAYSTACK_SECRET_KEY=SECRET)
    def test_failed_mpesa_prompt_still_sends_email(self):
        from .paystack import PaystackError
        def fake(method, path, **kwargs):
            if path == "/charge":
                raise PaystackError("Invalid phone")
            return {"authorization_url": "https://checkout.paystack.com/req3"}
        with patch("tracker.paystack._call", side_effect=fake):
            data = self.client.post("/api/payments/request/", {"member_id": self.john.id, "amount": "500", "mpesa": True}, format="json").json()
        self.assertEqual(data["mpesa"], {"sent": False, "detail": "Invalid phone"})
        self.assertEqual(len(mail.outbox), 1)

    def test_dashboard(self):
        pay(self.belinda, "30", "P1")
        pay(self.john, "3000", "P2")
        pay(self.john, "500", "P4")
        pay(self.john, "100", "P3", status="pending")
        data = self.client.get("/api/dashboard/").json()
        self.assertEqual((data["members"], data["completed"], data["in_progress"], data["pending"]), (2, 1, 1, 1))
        self.assertEqual(data["by_duration"], {"1wk": 0, "2wks": 2})  # members, not payments
        self.assertEqual(Decimal(data["raised"]), Decimal("3530"))

    def test_export_is_an_excel_file(self):
        pay(self.belinda, "30", "P1")
        response = self.client.get("/api/export/")
        self.assertTrue(response.content.startswith(b"PK"))
