import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from geo.models import Location


def parse_unlocode_coordinates(coord_str: str):
    """
    UN/LOCODE format: DDMMN DDDMME, DDMMN DDDMMW, dll.
    Contoh: '0607S 10651E'
    Return: (lat, lon) float atau (None, None) kalau gagal.
    """
    if not coord_str:
        return None, None
    coord_str = coord_str.strip()
    try:
        lat_part, lon_part = coord_str.split()
        # LAT
        lat_deg = int(lat_part[0:2])
        lat_min = int(lat_part[2:4])
        lat_sign = -1 if lat_part[4] == "S" else 1
        lat = lat_sign * (lat_deg + lat_min / 60.0)
        # LON
        lon_deg = int(lon_part[0:3])
        lon_min = int(lon_part[3:5])
        lon_sign = -1 if lon_part[5] == "W" else 1
        lon = lon_sign * (lon_deg + lon_min / 60.0)
        return lat, lon
    except Exception:
        return None, None


class Command(BaseCommand):
    help = "Import UN/LOCODE ports for Indonesia into Location (kind=port / offshore-terminal)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to UN/LOCODE code-list.csv",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise SystemExit(f"File not found: {path}")

        self.stdout.write(f"Reading {path} ...")

        # pastikan country Indonesia sudah ada
        country, _ = Location.objects.get_or_create(
            code="ID",
            defaults={"name": "Indonesia", "kind": "country", "parent": None},
        )

        created = 0
        updated = 0
        skipped = 0

        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Country"] != "ID":
                    continue  # hanya Indonesia

                func = row["Function"] or ""
                # hanya lokasi yang punya fungsi '1' (port) atau '7' (offshore/fixed) saja
                is_port = len(func) >= 1 and func[0] == "1"
                is_fixed = len(func) >= 7 and func[6] == "7"

                if not (is_port or is_fixed):
                    continue

                locode = f"{row['Country']}{row['Location']}"  # contoh: IDJKT
                name = (row["Name"] or "").strip()
                coords = (row["Coordinates"] or "").strip()

                latitude, longitude = parse_unlocode_coordinates(coords)

                kind = "port"
                if is_fixed and not is_port:
                    kind = "offshore-terminal"

                # parent: kita coba mapping kasar ke province via subdivision code (opsional)
                parent = None
                subdiv = (row["Subdivision"] or "").strip()
                if subdiv:
                    # misal: Subdivision = 'JB' untuk Jawa Barat dst, tergantung isi unlocode
                    # Kalau om punya mapping ke Location province, bisa improve di sini.
                    # Untuk sementara, biarkan parent None (nanti bisa di-update script lain).
                    pass

                obj, created_flag = Location.objects.update_or_create(
                    code=locode,
                    defaults={
                        "name": name,
                        "kind": kind,
                        "parent": parent or country,  # sementara parent = country
                        "unlocode": locode,
                        "latitude": latitude,
                        "longitude": longitude,
                        "country_code": "ID",
                        "status": "active",
                        "source": "UNLOCODE",
                    },
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Ports created: {created}, updated: {updated}, skipped(non-port): {skipped}"
        ))
