from django.core.management.base import BaseCommand

from tracker import paystack
from tracker.models import Payment


class Command(BaseCommand):
    help = "Check pending Paystack payments with Paystack and update their status."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, limit, **options):
        before = Payment.objects.filter(status=Payment.PENDING, source="paystack").count()
        paystack.sync_pending(Payment.objects.all(), limit=limit)
        after = Payment.objects.filter(status=Payment.PENDING, source="paystack").count()
        self.stdout.write(self.style.SUCCESS(f"Updated {before - after} payment(s); {after} still pending."))
