from django.core.management.base import BaseCommand
from partners.models import Partner, PartnerRole

SEED = [
    ("PT Agency Satu",   "agency"),
    ("PT Agency Dua",    "agency"),
    ("CV Vendor Satu",   "vendor"),
    ("CV Vendor Dua",    "vendor"),
    ("PT Carrier Satu",  "carrier"),
    ("PT Carrier Dua",   "carrier"),
    ("PT Customer Satu", "customer"),
    ("PT Customer Dua",  "customer"),
    ("PT Customer Tiga", "customer"),
    ("PT Customer Empat","customer"),
]

class Command(BaseCommand):
    help = "Seed 10 partners dengan roles"

    def handle(self, *args, **options):
        created_count = 0
        for name, role in SEED:
            partner, created = Partner.objects.get_or_create(
                name=name,
                defaults={
                    "email": f"{name.replace(' ', '').lower()}@example.com",
                    "phone": "021-123456",
                    "tax": "NPWP123456",
                    "address": "Jl. Contoh No. 1",
                    "city": "Jakarta",
                    "country": "Indonesia",
                    "postcode": "10110",
                },
            )
            # tambahkan role (abaikan jika sudah ada)
            PartnerRole.objects.get_or_create(partner=partner, role=role)
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed partners selesai. Baru dibuat: {created_count}, total: {Partner.objects.count()}"
        ))
