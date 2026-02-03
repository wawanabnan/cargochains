from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

from shipments.models import Shipment, ShipmentEvent, ShipmentDocument
from shipments.services.status_rollup import recompute_shipment_status

# NOTE: Location wajib buat Shipment (origin/destination). Ambil dari geo.Location.
from geo.models import Location


def aware(y, m, d, hh, mm):
    # buat datetime aware mengikuti TIME_ZONE Django
    return timezone.make_aware(datetime(y, m, d, hh, mm))


class Command(BaseCommand):
    help = "Seed demo shipment tracking timeline + POD for public tracking demo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tracking",
            type=str,
            default="SHP202602-00001",
            help="Tracking number to use (default: SHP202602-00001). If not found, will create a new shipment.",
        )

    def handle(self, *args, **options):
        tracking_no = options["tracking"]

        # 1) Ensure we have at least one Location
        loc_qs = Location.objects.all().order_by("id")
        if not loc_qs.exists():
            self.stderr.write(self.style.ERROR("No Location found. Create at least 1 geo.Location first."))
            return

        origin = loc_qs.first()
        destination = loc_qs.last()  # if only one, it will be same as origin

        # 2) Get or create shipment
        shipment = Shipment.objects.filter(tracking_no=tracking_no).first()
        created = False

        if shipment is None:
            shipment = Shipment.objects.create(
                origin=origin,
                destination=destination,
                status="DRAFT",
            )
            # tracking_no auto-generated in save() if empty; but we want fixed tracking for demo
            shipment.tracking_no = tracking_no
            shipment.save(update_fields=["tracking_no"])
            created = True

        # 3) Helper to create events with dedupe_key
        def upsert_event(code, event_time, location_text, note, is_public=True, affects_status=True, dedupe_key=None):
            if not dedupe_key:
                dedupe_key = f"demo:{shipment.id}:{code}:{event_time.isoformat()}"

            ev, _ = ShipmentEvent.objects.get_or_create(
                shipment=shipment,
                dedupe_key=dedupe_key,
                defaults=dict(
                    code=code,
                    event_time=event_time,
                    location_text=location_text,
                    note=note,
                    is_public=is_public,
                    affects_status=affects_status,
                    source="SYSTEM",
                ),
            )
            return ev

        # 4) Seed timeline (public)
        upsert_event(
            code="PICKUP_SCHEDULED",
            event_time=aware(2026, 2, 1, 9, 0),
            location_text="Jakarta",
            note="",
            is_public=True,
            affects_status=True,
            dedupe_key=f"demo:{shipment.id}:PICKUP_SCHEDULED",
        )
        upsert_event(
            code="PICKUP_DISPATCHED",
            event_time=aware(2026, 2, 1, 11, 30),
            location_text="",
            note="",
            is_public=True,
            affects_status=True,
            dedupe_key=f"demo:{shipment.id}:PICKUP_DISPATCHED",
        )
        upsert_event(
            code="ARRIVED",
            event_time=aware(2026, 2, 2, 3, 10),
            location_text="Bandung Hub",
            note="",
            is_public=True,
            affects_status=True,
            dedupe_key=f"demo:{shipment.id}:ARRIVED",
        )
        upsert_event(
            code="OUTFORDELIVERY",
            event_time=aware(2026, 2, 2, 8, 0),
            location_text="Bandung",
            note="",
            is_public=True,
            affects_status=True,
            dedupe_key=f"demo:{shipment.id}:OUTFORDELIVERY",
        )
        upsert_event(
            code="DELIVERED",
            event_time=aware(2026, 2, 2, 10, 5),
            location_text="Bandung",
            note="Paket diterima",
            is_public=True,
            affects_status=True,
            dedupe_key=f"demo:{shipment.id}:DELIVERED",
        )

        # 5) Seed POD document (public)
        doc = ShipmentDocument.objects.filter(shipment=shipment, doc_type="POD").order_by("-uploaded_at", "-id").first()
        if doc is None:
            doc = ShipmentDocument.objects.create(
                shipment=shipment,
                doc_type="POD",
                file=ContentFile(b"Demo POD - received by Budi", name="pod_demo.txt"),
                is_public=True,
            )
            # make uploaded_at after delivered for nicer demo
            ShipmentDocument.objects.filter(id=doc.id).update(uploaded_at=aware(2026, 2, 2, 10, 10))

        # 6) Recompute status to ensure shipment.status = DELIVERED
        recompute_shipment_status(shipment)
        shipment.refresh_from_db()

        # 7) Print output
        self.stdout.write(self.style.SUCCESS("✅ Demo tracking seeded successfully"))
        self.stdout.write(f"Tracking No : {shipment.tracking_no}")
        self.stdout.write(f"Status      : {shipment.status}")
        self.stdout.write(f"Public URL  : /api/public/track/{shipment.tracking_no}/")
        if created:
            self.stdout.write(self.style.WARNING("Note: Shipment was created using first/last Location in DB."))
