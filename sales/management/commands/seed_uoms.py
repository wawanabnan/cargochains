from django.core.management.base import BaseCommand
from sales.models import UOM

DEFAULT_UOMS = [
    ("PCS", "Pieces"),
    ("KG",  "Kilogram"),
    ("TON", "Ton"),
    ("CBM", "Cubic Meter"),
    ("PKG", "Package"),
]

class Command(BaseCommand):
    help = "Seed default Unit of Measurement (UOM) records."

    def handle(self, *args, **options):
        created = 0
        for code, name in DEFAULT_UOMS:
            obj, was_created = UOM.objects.get_or_create(code=code, defaults={"name": name})
            created += 1 if was_created else 0
        self.stdout.write(self.style.SUCCESS(f"UOM seeding done. New rows: {created}, total: {UOM.objects.count()}"))
