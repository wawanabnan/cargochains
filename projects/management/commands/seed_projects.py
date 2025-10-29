from django.core.management.base import BaseCommand
from projects.models import ProjectCategory, CostCategory

class Command(BaseCommand):
    help = "Seed basic categories for projects app"

    def handle(self, *args, **options):
        pc = [("RGS", "Reguler Shipments"), ("PSH", "Project Shipment"), ("SHC", "Ship Charter")]
        cc = [("FUEL", "Fuel"), ("LAB", "Labor"), ("DOC", "Document"), ("TRN", "Transport")]
        for code, name in pc:
            ProjectCategory.objects.get_or_create(code=code, defaults={"name": name})
        for code, name in cc:
            CostCategory.objects.get_or_create(code=code, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS("Seeded project & cost categories."))
