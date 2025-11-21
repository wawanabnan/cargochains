import json
import math
import re

from django.core.management.base import BaseCommand, CommandError
from geo.models import Location


RADIUS_M = 300  # radius cluster dalam meter


def haversine(lat1, lon1, lat2, lon2):
    """Hitung jarak dua titik (meter)."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def jet_code_from_osm_id(osm_id: str) -> str | None:
    """Bikin kode JET-xxxx dari @id OSM (way/25763507 -> JET-25763507)."""
    if not osm_id:
        return None
    digits = re.sub(r"\D+", "", osm_id)
    if not digits:
        return None
    return f"JET-{digits}"


class Command(BaseCommand):
    help = "Import jetty Indonesia dari OSM GeoJSON (export Overpass), dengan filter dan deduplikasi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path ke export.geojson OSM (hasil Overpass).",
        )

    def handle(self, *args, **options):
        path = options["file"]

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError as e:
            raise CommandError(f"Gagal membuka file {path}: {e}")
        except json.JSONDecodeError as e:
            raise CommandError(f"File {path} bukan JSON valid: {e}")

        features = data.get("features", [])
        if not features:
            self.stdout.write(self.style.WARNING("Tidak ada fitur di GeoJSON."))
            return

        self.stdout.write(self.style.WARNING(f"Total fitur di GeoJSON: {len(features)}"))

        # Step 1: pilih kandidat jetty yang relevan
        candidates = []
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            name = (props.get("name") or "").strip()

            if not name:
                # Buang semua pier tanpa nama
                continue

            # Harus pier atau harbour (ini yang tadi kelihatan di file om)
            man_made = props.get("man_made")
            harbour = props.get("harbour")

            if not (man_made == "pier" or harbour == "yes"):
                continue

            if geom.get("type") != "Point":
                continue

            coords = geom.get("coordinates") or []
            if len(coords) != 2:
                continue

            lon, lat = coords
            if lat is None or lon is None:
                continue

            candidates.append(
                {
                    "name": name,
                    "lat": float(lat),
                    "lon": float(lon),
                    "props": props,
                }
            )

        self.stdout.write(self.style.WARNING(f"Kandidat jetty bernama: {len(candidates)}"))

        # Step 2: cluster per name + radius (untuk menghilangkan duplikasi Dermaga 2 dst.)
        clusters: list[dict] = []

        for cand in candidates:
            name = cand["name"]
            lat = cand["lat"]
            lon = cand["lon"]

            assigned = False
            for c in clusters:
                if c["name"] != name:
                    continue
                dist = haversine(lat, lon, c["center_lat"], c["center_lon"])
                if dist <= RADIUS_M:
                    c["points"].append(cand)
                    # update centroid
                    c["center_lat"] = sum(p["lat"] for p in c["points"]) / len(c["points"])
                    c["center_lon"] = sum(p["lon"] for p in c["points"]) / len(c["points"])
                    assigned = True
                    break

            if not assigned:
                clusters.append(
                    {
                        "name": name,
                        "center_lat": lat,
                        "center_lon": lon,
                        "points": [cand],
                    }
                )

        self.stdout.write(self.style.WARNING(f"Cluster jetty unik: {len(clusters)}"))

        # Step 3: simpan ke DB (1 jetty per cluster)
        created = 0
        for cluster in clusters:
            name = cluster["name"]
            lat = cluster["center_lat"]
            lon = cluster["center_lon"]

            # pakai feature pertama di cluster sebagai referensi @id
            props = cluster["points"][0]["props"]
            osm_id = props.get("@id") or props.get("id")
            code = jet_code_from_osm_id(osm_id) or None

            # kalau code None, generate fallback dari nama+latlon (jarang terjadi)
            if not code:
                safe_name = re.sub(r"[^A-Z0-9]+", "-", name.upper())[:16]
                code = f"JET-{safe_name}"

            obj, is_created = Location.objects.get_or_create(
                code=code,
                defaults=dict(
                    name=name,
                    kind="jetty",
                    latitude=lat,
                    longitude=lon,
                    country_code="ID",
                    status="active",
                    source="OSM Jetty",
                    display_name=name,
                ),
            )
            if is_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Jetty baru dibuat: {created} lokasi"))
