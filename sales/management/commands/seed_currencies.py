from django.core.management.base import BaseCommand
from sales.models import Currency  # sesuaikan kalau model Currency ada di app lain

class Command(BaseCommand):
    help = "Seed default currencies"

    def handle(self, *args, **options):
        data = [
            {"code": "IDR", "name": "Indonesian Rupiah"},
            {"code": "USD", "name": "US Dollar"},
            {"code": "EUR", "name": "Euro"},
            {"code": "JPY", "name": "Japanese Yen"},
            {"code": "SGD", "name": "Singapore Dollar"},
        ]
        for item in data:
            obj, created = Currency.objects.get_or_create(code=item["code"], defaults={"name": item["name"]})
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {obj.code}"))
            else:
                self.stdout.write(self.style.WARNING(f"{obj.code} already exists"))

        # jadikan IDR sebagai default (kalau model punya field flag misal is_default)
        if hasattr(Currency, "is_default"):
            Currency.objects.update(is_default=False)
            Currency.objects.filter(code="IDR").update(is_default=True)
            self.stdout.write(self.style.SUCCESS("Set IDR as default currency"))
