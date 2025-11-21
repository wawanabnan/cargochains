import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from geo.models import Location


class Command(BaseCommand):
    help = "Import Indonesian airports from OurAirports into Location (kind=airport)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to OurAirports airports_id.csv",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise SystemExit(f"File not found: {path}")

        country, _ = Location.objects.get_or_create(
            code="ID",
            defaults={"name": "Indonesia", "kind": "country", "parent": None}
        )

        created = 0
        updated = 0

        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("iso_country") != "ID":
                    continue

                # skip heliport atau sejenis jika tidak perlu
                if r["type"] not in ("large_airport", "medium_airport", "small_airport"):
                    continue

                iata = (r.get("iata_code") or "").strip()
                ident = (r.get("ident") or "").strip()
                name = (r.get("name") or "").strip()
                lat = r.get("latitude_deg")
                lon = r.get("longitude_deg")

                try:
                    latitude = float(lat) if lat else None
                    longitude = float(lon) if lon else None
                except ValueError:
                    latitude = longitude = None

                # pilih code: utamakan IATA, fallback ke ICAO
                if iata:
                    code = iata.upper()
                else:
                    code = f"AIR-{ident}"

                obj, flag = Location.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "kind": "airport",
                        "parent": country,  # nanti bisa di-refine ke kota/region
                        "iata_code": iata or None,
                        "latitude": latitude,
                        "longitude": longitude,
                        "country_code": "ID",
                        "status": "active",
                        "source": "OurAirports",
                    },
                )
                if flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Airports imported. Created: {created}, Updated: {updated}"
        ))
