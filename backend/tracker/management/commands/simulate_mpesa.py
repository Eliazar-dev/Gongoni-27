"""Test the whole payment flow without a phone.

Example:
  python manage.py simulate_mpesa --name "Belinda Boyani Mayore" --phone 254707548406 --amount 1000
"""
import random
import string

from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.services.ingest import process_incoming


class Command(BaseCommand):
    help = "Pretend the treasurer's phone just received an M-Pesa Paybill message."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--phone", required=True, help="Payer phone, for example 254707548406")
        parser.add_argument("--amount", required=True)
        parser.add_argument("--account", default="mission commitment")
        parser.add_argument("--code", default="")

    def handle(self, *args, **opts):
        code = opts["code"] or "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        now = timezone.localtime()
        text = (
            f"{code} Confirmed. on {now:%d/%m/%y} at {now:%I:%M %p}".replace(" 0", " ")
            + f" Ksh{float(opts['amount']):,.2f} received from {opts['name']} {opts['phone']}.  "
            f"Account Number {opts['account']}  New Utility balance is Ksh1,000.00"
        )
        self.stdout.write("Message: " + text)
        self.stdout.write("Result:  " + process_incoming("MPESA", text))
