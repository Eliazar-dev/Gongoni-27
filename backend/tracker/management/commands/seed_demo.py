"""Fill the system with fake members and payments so you can try every page.

  python manage.py seed_demo          add demo data
  python manage.py seed_demo --clear  remove the demo data again
No emails are sent. Demo members use emails ending in @demo.invalid.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Member, Payment

PEOPLE = [
    ("Grace Wanjiru Kamau", "1wk", [1000, 1500, 1000]),
    ("Brian Otieno Odhiambo", "2wks", [3500]),
    ("Faith Achieng Ouma", "2wks", [500]),
    ("Samuel Kiprono Rotich", "1wk", []),
    ("Mercy Naliaka Wekesa", "2wks", [2000, 1000]),
    ("Daniel Mutua Musyoka", "1wk", [3500]),
    ("Esther Nyambura Njoroge", "2wks", []),
    ("Peter Omondi Onyango", "1wk", [700]),
    ("Lucy Chebet Koech", "2wks", [1750, 1750]),
    ("Joseph Karanja Mwangi", "2wks", []),
    ("Ruth Akinyi Otieno", "1wk", [3000]),
    ("Kelvin Mwenda Kimathi", "2wks", [250]),
]


class Command(BaseCommand):
    help = "Create (or remove) demo members and payments."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **opts):
        demo = Member.objects.filter(email__endswith="@demo.invalid")
        if opts["clear"]:
            Payment.objects.filter(member__in=demo).delete()
            count = demo.count()
            demo.delete()
            self.stdout.write(f"Removed {count} demo members.")
            return

        now = timezone.now()
        counter = 0
        for index, (name, duration, payments) in enumerate(PEOPLE, start=1):
            phone = f"2547000000{index:02d}"
            member, created = Member.objects.get_or_create(
                phone=phone,
                defaults={
                    "name": name,
                    "email": f"demo{index}@demo.invalid",
                    "duration": duration,
                },
            )
            if not created:
                continue
            for n, amount in enumerate(payments):
                counter += 1
                Payment.objects.create(
                    reference=f"DEMO{index:02d}{n:02d}{counter:04d}",
                    amount=Decimal(amount),
                    paid_at=now - timedelta(days=(index + n * 3) % 12, hours=n),
                    member=member,
                    status=Payment.SUCCESS,
                    channel="mobile_money",
                )
        self.stdout.write(self.style.SUCCESS("Demo data ready. Remove it with: python manage.py seed_demo --clear"))
