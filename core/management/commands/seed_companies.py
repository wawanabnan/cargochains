from django.core.management.base import BaseCommand
from core.models import CoreSetting, CompanyProfile


class Command(BaseCommand):
    help = "Seed initial core data (settings, company)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Seeding Core Data ==="))

        # === 1. Core Settings ===
        settings_data = [
            {
                "code": "quotation_valid_days",
                "int_value": 7,
                "notes": "Masa berlaku quotation (hari)",
            },
        ]
        for data in settings_data:
            obj, created = CoreSetting.objects.get_or_create(code=data["code"], defaults=data)
            self.stdout.write(self.style.SUCCESS(f"{'[+]' if created else '[=]'} Setting: {obj.code}"))

        # === 2. Company Info ===
        company_data = {
            "name": "PT. Dakara Samudera Hanasta",
            "brand": "Dakarash",
            "address": "Jl. Raya Ancol Barat No. 10, Jakarta Utara",
            "phone": "+62-21-xxxxxxx",
            "email": "info@dakarash.co.id",
            "website": "https://dakarash.co.id",
            "is_default": True,
        }
        company, created = CompanyProfile.objects.get_or_create(
            name=company_data["name"],
            defaults=company_data,
        )
        self.stdout.write(self.style.SUCCESS(f"{'[+]' if created else '[=]'} Company: {company.name}"))
