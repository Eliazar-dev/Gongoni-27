from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import IncomingMessage, Member, PayerAlias, Payment
from .services import matching
from .services.ingest import process_incoming
from .services.notify import build_receipt, member_progress
from .services.parser import parse_mpesa_message, sanitize_message
from .services.phones import normalize_phone

SAMPLE = (
    "UJL11B2KXF Confirmed. on 21/10/26 at 5:33 PM Ksh30.00 received from Belinda Boyani Mayore "
    "254707548406.  Account Number mission commitment  New Utility balance is Ksh241,585.00"
)


def make_member(name="Belinda Boyani Mayore", phone="254707548406", mpesa=None, email="belinda@example.org", **kw):
    return Member.objects.create(
        name=name, phone=phone, mpesa_phone=mpesa or phone, email=email, duration=kw.pop("duration", "2wks"), **kw
    )


def sms_text(code, name, phone, amount="1,000.00", account="mission commitment"):
    return (
        f"{code} Confirmed. on 22/10/26 at 9:05 AM Ksh{amount} received from {name} {phone}.  "
        f"Account Number {account}  New Utility balance is Ksh241,585.00"
    )


class PhoneTests(TestCase):
    def test_formats(self):
        for raw in ["0712 345 678", "+254712345678", "254712345678", "712345678", "0112345678"]:
            self.assertIsNotNone(normalize_phone(raw), raw)
        self.assertEqual(normalize_phone("0712 345 678"), "254712345678")
        self.assertEqual(normalize_phone("0112345678"), "254112345678")

    def test_invalid(self):
        for raw in ["", "12345", "0612345678", "254712", "abc", "2547123456789"]:
            self.assertIsNone(normalize_phone(raw), raw)


class ParserTests(TestCase):
    def test_real_sample_message(self):
        p = parse_mpesa_message(SAMPLE)
        self.assertEqual(p.code, "UJL11B2KXF")
        self.assertEqual(p.amount, Decimal("30.00"))
        self.assertEqual(p.payer_name, "Belinda Boyani Mayore")
        self.assertEqual(p.payer_phone, "254707548406")
        self.assertEqual(p.account, "mission commitment")
        self.assertEqual(timezone.localtime(p.paid_at).strftime("%Y-%m-%d %H:%M"), "2026-10-21 17:33")

    def test_big_amount_with_commas(self):
        p = parse_mpesa_message(sms_text("AAA1BBB2CC", "John Doe", "254700111222", amount="1,500.50"))
        self.assertEqual(p.amount, Decimal("1500.50"))

    def test_masked_phone_keeps_name(self):
        p = parse_mpesa_message(sms_text("AAA1BBB2CC", "John Doe", "2547****2222"))
        self.assertEqual(p.payer_phone, "")
        self.assertEqual(p.payer_name, "John Doe")

    def test_phone_before_name(self):
        p = parse_mpesa_message(sms_text("AAA1BBB2CC", "254700111222", "JOHN DOE"))
        self.assertEqual(p.payer_phone, "254700111222")
        self.assertEqual(p.payer_name, "JOHN DOE")

    def test_not_an_mpesa_message(self):
        self.assertIsNone(parse_mpesa_message("Hello, your airtime is low"))
        self.assertIsNone(parse_mpesa_message(""))

    def test_balance_is_removed(self):
        self.assertNotIn("241,585", sanitize_message(SAMPLE))
        self.assertIn("UJL11B2KXF", sanitize_message(SAMPLE))


class MatchingTests(TestCase):
    def setUp(self):
        self.belinda = make_member()
        self.john = make_member("John Kamau Mwangi", "254711111111", email="john@example.org")

    def test_phone_beats_name(self):
        result = matching.find_member("254707548406", "Someone Else")
        self.assertEqual((result.member, result.how), (self.belinda, matching.PHONE))

    def test_mpesa_phone_differs_from_phone(self):
        self.john.mpesa_phone = "254722222222"
        self.john.save()
        self.assertEqual(matching.find_member("254722222222", "").member, self.john)

    def test_exact_name_any_order_and_case(self):
        result = matching.find_member("", "MAYORE BELINDA BOYANI")
        self.assertEqual((result.member, result.how), (self.belinda, matching.NAME))

    def test_close_name_needs_review(self):
        result = matching.find_member("", "BELINDA MAYORE")
        self.assertEqual((result.member, result.how), (self.belinda, matching.CLOSE))

    def test_one_shared_name_is_not_enough(self):
        self.assertIsNone(matching.find_member("", "Belinda Wanjiku").member)

    def test_no_match(self):
        self.assertIsNone(matching.find_member("254733333333", "Nobody Known").member)

    def test_two_members_same_phone_is_ambiguous(self):
        self.john.mpesa_phone = self.belinda.phone
        self.john.save()
        result = matching.find_member(self.belinda.phone, "")
        self.assertTrue(result.ambiguous)
        self.assertIsNone(result.member)

    def test_remembered_payer_matches_next_time(self):
        matching.remember_payer(self.john, "254799999999", "Mary Wanjiru Kamau")
        self.assertEqual(matching.find_member("254799999999", "").member, self.john)
        self.assertEqual(matching.find_member("", "Kamau Mary Wanjiru").member, self.john)

    def test_inactive_members_are_ignored(self):
        self.belinda.is_active = False
        self.belinda.save()
        self.assertIsNone(matching.find_member("254707548406", "Belinda Boyani Mayore").member)


@override_settings(NOTIFY_ASYNC=False, WEBHOOK_SECRET="s3cret", SMS_BACKEND="console")
class IngestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.member = make_member()

    @patch("tracker.services.notify.send_sms", return_value=(True, ""))
    def test_sample_message_is_recorded_and_member_notified(self, sms):
        self.assertEqual(process_incoming("MPESA", SAMPLE), "recorded")
        payment = Payment.objects.get()
        self.assertEqual((payment.member, payment.amount, payment.status), (self.member, Decimal("30"), "recorded"))
        self.assertTrue(payment.receipt_no.startswith("RC-"))
        self.assertNotIn("241,585", payment.raw_message)
        # email first, with receipt and progress
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["belinda@example.org"])
        self.assertIn("KES 3,470", mail.outbox[0].body)  # balance
        self.assertIn("0%", mail.outbox[0].body)
        # then SMS
        sms.assert_called_once()
        self.assertIn("Receipt " + payment.receipt_no, sms.call_args[0][1])

    def test_other_sender_is_ignored(self):
        self.assertEqual(process_incoming("MYBANK", SAMPLE), "ignored")
        self.assertEqual(Payment.objects.count(), 0)

    def test_sender_case_does_not_matter(self):
        self.assertEqual(process_incoming("mpesa", SAMPLE), "recorded")

    def test_unreadable_message_is_logged(self):
        self.assertEqual(process_incoming("MPESA", "XYZ Confirmed. something odd"), "unparsed")
        self.assertEqual(IncomingMessage.objects.get().status, "unparsed")

    def test_tithe_is_not_a_mission_payment(self):
        self.assertEqual(process_incoming("MPESA", sms_text("TTT1TTT2TT", "John Doe", "254700000000", account="tithe")), "not_mission")
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_same_code_twice_is_counted_once(self):
        self.assertEqual(process_incoming("MPESA", SAMPLE), "recorded")
        self.assertEqual(process_incoming("MPESA", SAMPLE), "duplicate")
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_close_name_waits_for_confirmation(self):
        status = process_incoming("MPESA", sms_text("CCC1CCC2CC", "BELINDA MAYORE", "254799000111"))
        self.assertEqual(status, "review")
        payment = Payment.objects.get()
        self.assertEqual((payment.member, payment.suggested_member), (None, self.member))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(member_progress(self.member)["paid"], 0)

    def test_unknown_payer_is_unassigned(self):
        self.assertEqual(process_incoming("MPESA", sms_text("UUU1UUU2UU", "Stranger Person", "254799000111")), "unassigned")
        self.assertEqual(len(mail.outbox), 0)

    def test_member_without_email_still_gets_sms(self):
        self.member.email = ""
        self.member.save()
        with patch("tracker.services.notify.send_sms", return_value=(True, "")) as sms:
            process_incoming("MPESA", SAMPLE)
        self.assertEqual(len(mail.outbox), 0)
        sms.assert_called_once()

    def test_sms_failure_does_not_lose_payment(self):
        with patch("tracker.services.notify.send_sms", return_value=(False, "no credit")):
            self.assertEqual(process_incoming("MPESA", SAMPLE), "recorded")
        self.assertEqual(Payment.objects.filter(status="recorded").count(), 1)
        self.assertEqual(self.member.notifications.filter(channel="sms", status="failed").count(), 1)

    def test_webhook_needs_the_secret(self):
        client = APIClient()
        body = {"from": "MPESA", "text": SAMPLE}
        self.assertEqual(client.post("/api/webhook/sms/", body, format="json").status_code, 403)
        self.assertEqual(client.post("/api/webhook/sms/?key=wrong", body, format="json").status_code, 403)
        self.assertEqual(Payment.objects.count(), 0)
        ok = client.post("/api/webhook/sms/?key=s3cret", body, format="json")
        self.assertEqual((ok.status_code, ok.json()["status"]), (200, "recorded"))

    def test_webhook_accepts_header_secret(self):
        response = APIClient().post(
            "/api/webhook/sms/", {"from": "MPESA", "text": SAMPLE}, format="json", HTTP_X_WEBHOOK_SECRET="s3cret"
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(WEBHOOK_SECRET="")
    def test_webhook_closed_when_no_secret_configured(self):
        response = APIClient().post("/api/webhook/sms/?key=", {"from": "MPESA", "text": SAMPLE}, format="json")
        self.assertEqual(response.status_code, 403)


class ReceiptTests(TestCase):
    def pay(self, member, amount, code):
        return Payment.objects.create(
            mpesa_code=code, amount=Decimal(amount), paid_at=timezone.now(), member=member, status="recorded"
        )

    def test_percentages_and_balance(self):
        member = make_member()
        payment = self.pay(member, "1000", "P1")
        progress = member_progress(member)
        self.assertEqual((progress["percent"], progress["balance"]), (28, Decimal("2500")))
        self.assertIn("(28% of 3,500)", build_receipt(payment, member)["sms"])

    def test_never_shows_100_before_completion(self):
        member = make_member()
        self.pay(member, "3499", "P1")
        self.assertEqual(member_progress(member)["percent"], 99)

    def test_completion_message(self):
        member = make_member()
        self.pay(member, "2000", "P1")
        last = self.pay(member, "1500", "P2")
        receipt = build_receipt(last, member)
        self.assertTrue(receipt["completed"])
        self.assertIn("Congratulations", receipt["sms"])
        self.assertEqual(member_progress(member)["balance"], 0)

    def test_reversed_and_unassigned_are_not_counted(self):
        member = make_member()
        self.pay(member, "1000", "P1")
        Payment.objects.create(mpesa_code="P2", amount=500, paid_at=timezone.now(), member=member, status="reversed")
        Payment.objects.create(mpesa_code="P3", amount=500, paid_at=timezone.now(), status="unassigned")
        self.assertEqual(member_progress(member)["paid"], Decimal("1000"))

    def test_sms_fits_one_message_for_typical_amounts(self):
        member = make_member()
        payment = self.pay(member, "1000", "P1")
        self.assertLessEqual(len(build_receipt(payment, member)["sms"]), 160)


@override_settings(NOTIFY_ASYNC=False)
class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.body = {
            "name": "Grace  wanjiru Kamau", "email": "Grace@Example.org", "phone": "0712 345 678",
            "duration": "2wks", "mpesa_phone": "0722 111 222",
        }

    def test_register(self):
        response = self.client.post("/api/register/", self.body, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        member = Member.objects.get()
        self.assertEqual(
            (member.name, member.email, member.phone, member.mpesa_phone, member.duration, member.target),
            ("Grace wanjiru Kamau", "grace@example.org", "254712345678", "254722111222", "2wks", Decimal("3500")),
        )
        self.assertRegex(member.code, r"^GN-\d{4}$")
        self.assertEqual(response.json()["code"], member.code)

    def test_welcome_email_is_sent(self):
        self.client.post("/api/register/", self.body, format="json")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("7108831", mail.outbox[0].body)
        self.assertIn("Mission Commitment", mail.outbox[0].body)

    def test_same_phone_cannot_register_twice(self):
        self.client.post("/api/register/", self.body, format="json")
        response = self.client.post("/api/register/", {**self.body, "phone": "+254712345678"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())
        self.assertEqual(Member.objects.count(), 1)

    def test_bad_inputs(self):
        for field, value in [
            ("phone", "12345"), ("mpesa_phone", "abc"), ("email", "nope"), ("duration", "3wks"), ("name", "Madonna"),
        ]:
            response = self.client.post("/api/register/", {**self.body, field: value}, format="json")
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json())

    def test_bot_trap_field(self):
        response = self.client.post("/api/register/", {**self.body, "website": "http://spam"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Member.objects.count(), 0)

    def test_public_config(self):
        data = self.client.get("/api/config/").json()
        self.assertEqual((data["paybill"], data["account_text"], data["target"]), ("7108831", "Mission Commitment", 3500))


@override_settings(NOTIFY_ASYNC=False, WEBHOOK_SECRET="s3cret")
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
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.json()["token"])

    def test_admin_endpoints_need_a_token(self):
        anon = APIClient()
        for path in ["/api/dashboard/", "/api/members/", "/api/payments/", "/api/export/", "/api/incoming/"]:
            self.assertEqual(anon.get(path).status_code, 401, path)

    def test_non_staff_token_is_refused(self):
        user = User.objects.create_user("plain", password="x12345678")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key)
        self.assertEqual(client.get("/api/members/").status_code, 403)

    def test_member_list_search_and_filters(self):
        process_incoming("MPESA", SAMPLE)  # Belinda pays 30
        rows = self.client.get("/api/members/").json()["results"]
        self.assertEqual(len(rows), 2)
        belinda = next(r for r in rows if r["name"] == "Belinda Boyani Mayore")
        self.assertEqual((float(belinda["paid"]), belinda["status"], belinda["percent"]), (30.0, "in_progress", 0))
        self.assertEqual(len(self.client.get("/api/members/?q=john").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?q=0711111111").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?status=unpaid").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?status=in_progress").json()["results"]), 1)
        self.assertEqual(len(self.client.get("/api/members/?status=completed").json()["results"]), 0)
        self.assertEqual(len(self.client.get("/api/members/?duration=1wk").json()["results"]), 0)

    def test_member_detail_and_edit(self):
        response = self.client.patch(f"/api/members/{self.john.id}/", {"email": "new@example.org", "phone": "0733 000 111"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.john.refresh_from_db()
        self.assertEqual((self.john.email, self.john.phone), ("new@example.org", "254733000111"))
        clash = self.client.patch(f"/api/members/{self.john.id}/", {"phone": self.belinda.phone}, format="json")
        self.assertEqual(clash.status_code, 400)

    def test_assign_unassigned_payment_and_remember_payer(self):
        process_incoming("MPESA", sms_text("UUU1UUU2UU", "Mary Wanjiru", "254799000111", amount="1,000.00"))
        payment = Payment.objects.get()
        self.assertEqual(payment.status, "unassigned")
        response = self.client.post(f"/api/payments/{payment.id}/assign/", {"member_id": self.john.id}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.member), ("recorded", self.john))
        self.assertEqual(mail.outbox[-1].to, ["john@example.org"])
        self.assertTrue(PayerAlias.objects.filter(kind="phone", value="254799000111", member=self.john).exists())
        # next payment from the same number goes straight to John
        self.assertEqual(process_incoming("MPESA", sms_text("UUU3UUU4UU", "Mary Wanjiru", "254799000111")), "recorded")
        self.assertEqual(Payment.objects.get(mpesa_code="UUU3UUU4UU").member, self.john)

    def test_confirm_suggested_payment(self):
        process_incoming("MPESA", sms_text("CCC1CCC2CC", "BELINDA MAYORE", "254799000111"))
        payment = Payment.objects.get()
        self.client.post(f"/api/payments/{payment.id}/assign/", {"member_id": payment.suggested_member_id}, format="json")
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.member, payment.suggested_member), ("recorded", self.belinda, None))

    def test_reverse_removes_from_totals_and_keeps_record(self):
        process_incoming("MPESA", SAMPLE)
        payment = Payment.objects.get()
        response = self.client.post(f"/api/payments/{payment.id}/reverse/", {"note": "wrong member"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(member_progress(self.belinda)["paid"], 0)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertIn("wrong member", Payment.objects.get().note)
        self.assertEqual(self.client.post(f"/api/payments/{payment.id}/reverse/", {}, format="json").status_code, 400)
        again = self.client.post(f"/api/payments/{payment.id}/assign/", {"member_id": self.john.id}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_manual_payment(self):
        body = {"member_id": self.john.id, "amount": "1500", "note": "paid in cash"}
        response = self.client.post("/api/payments/", body, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        payment = Payment.objects.get()
        self.assertEqual((payment.source, payment.status, payment.member), ("manual", "recorded", self.john))
        self.assertTrue(payment.mpesa_code.startswith("MANUAL-"))
        self.assertEqual(len(mail.outbox), 1)
        dup = self.client.post("/api/payments/", {**body, "mpesa_code": "ABC1234567"}, format="json")
        self.assertEqual(dup.status_code, 201)
        again = self.client.post("/api/payments/", {**body, "mpesa_code": "abc1234567"}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_payment_list_filters(self):
        process_incoming("MPESA", SAMPLE)
        process_incoming("MPESA", sms_text("UUU1UUU2UU", "Stranger Person", "254799000111"))
        self.assertEqual(self.client.get("/api/payments/?status=attention").json()["count"], 1)
        self.assertEqual(self.client.get("/api/payments/?status=recorded").json()["count"], 1)
        self.assertEqual(self.client.get("/api/payments/?q=stranger").json()["count"], 1)
        self.assertEqual(self.client.get("/api/payments/").json()["count"], 2)

    def test_dashboard(self):
        process_incoming("MPESA", SAMPLE)
        process_incoming("MPESA", sms_text("UUU1UUU2UU", "Stranger Person", "254799000111"))
        Payment.objects.create(mpesa_code="BIG1", amount=3500, paid_at=timezone.now(), member=self.john, status="recorded")
        data = self.client.get("/api/dashboard/").json()
        self.assertEqual((data["members"], data["completed"], data["unpaid"], data["in_progress"]), (2, 1, 0, 1))
        self.assertEqual((Decimal(data["raised"]), Decimal(data["target_total"])), (Decimal("3530"), Decimal("7000")))
        self.assertEqual((data["unassigned"], data["review"]), (1, 0))
        self.assertEqual(len(data["daily"]), 14)
        self.assertEqual(data["by_duration"]["2wks"], 2)

    def test_resend(self):
        process_incoming("MPESA", SAMPLE)
        payment = Payment.objects.get()
        before = len(mail.outbox)
        self.assertEqual(self.client.post(f"/api/payments/{payment.id}/resend/").status_code, 200)
        self.assertEqual(len(mail.outbox), before + 1)

    def test_export_is_an_excel_file(self):
        process_incoming("MPESA", SAMPLE)
        response = self.client.get("/api/export/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_incoming_log(self):
        process_incoming("MPESA", "garbled text")
        self.assertEqual(self.client.get("/api/incoming/?status=unparsed").json()["count"], 1)

    def test_spa_fallback_does_not_hide_api_404(self):
        self.assertEqual(self.client.get("/api/nothing/").status_code, 404)
