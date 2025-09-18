from django.core.management.base import BaseCommand
from sales.models import SalesService

ROWS = [
    ("D2D_SEA", "Sea - Door to Door", 10),
    ("D2P_SEA", "Sea - Door to Port", 20),
    ("P2P_SEA", "Sea - Port to Port", 30),
    ("D2D_AIR", "Air - Door to Door", 40),
    ("D2A_AIR", "Air - Door to Airport", 50),
    ("A2D_AIR", "Air - Airport to Door", 60),
    ("TRK",     "Inland - Trucking",    70),
]

class Command(BaseCommand):
    help = "Seed flat sales services"

    def handle(self, *args, **opts):
        created = 0
        for code, name, sort in ROWS:
            _, was_created = SalesService.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "sort_order": sort,
                    "is_active": True,
                }
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded services. New rows: {created}, total: {SalesService.objects.count()}"))
