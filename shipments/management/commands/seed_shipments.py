from django.core.management.base import BaseCommand
from django.utils import timezone
from shipments.models import TransportationType, Shipment, ShipmentRoute
from partners.models import Partner
from geo.models import Location

class Command(BaseCommand):
    help = "Seed initial shipments data"

    def handle(self, *args, **options):
        # Seed Transportation Types
        modes = [
            ("SEA", "SEA"), ("AIR", "AIR"), ("LAND", "LAND")
        ]
        for name, mode in modes:
            obj, created = TransportationType.objects.get_or_create(
                name=name, transportation_mode=mode
            )
            if created:
               self.stdout.write(f"Public URL  : /track/{shipment.tracking_no}/")

        # Dummy partners & locations (ambil pertama yg ada)
        shipper = Partner.objects.first()
        consignee = Partner.objects.last()
        carrier = Partner.objects.first()
        agency = Partner.objects.last()
        origin = Location.objects.first()
        destination = Location.objects.last()

        if not all([shipper, consignee, carrier, agency, origin, destination]):
            self.stdout.write(self.style.ERROR("Please add at least 2 partners and 2 locations first."))
            return

        # Seed Shipment
        shipment, created = Shipment.objects.get_or_create(
            number="SHP-0001",
            defaults=dict(
                origin=origin,
                destination=destination,
                shipper=shipper,
                consignee=consignee,
                carrier=carrier,
                agency=agency,
                etd=timezone.now().date(),
                eta=timezone.now().date(),
                cargo_description="Seed cargo example",
                qty=10,
                weight=1000,
                volume=20,
                status="DRAFT",
                total=5000,
            )
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Shipment {shipment.number}"))

        # Seed Route
        ttype = TransportationType.objects.first()
        ShipmentRoute.objects.get_or_create(
            shipment=shipment,
            origin=origin,
            destination=destination,
            transportation_type=ttype,
        )

        self.stdout.write(self.style.SUCCESS("Seeding done."))
