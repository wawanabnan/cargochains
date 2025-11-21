from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import csv
import os

from geo.models import Location


class Command(BaseCommand):
    help = (
        "Import hirarki wilayah administrasi Indonesia (Kemendagri) "
        "dari 4 file CSV: provinces, regencies, districts, villages."
    )

    def add_arguments(self, parser):
        parser.add_argument("--provinces", required=True, help="Path ke provinces.csv")
        parser.add_argument("--regencies", required=True, help="Path ke regencies.csv")
        parser.add_argument("--districts", required=True, help="Path ke districts.csv")
        parser.add_argument("--villages", required=True, help="Path ke villages.csv")

    def handle(self, *args, **options):
        provinces_path = options["provinces"]
        regencies_path = options["regencies"]
        districts_path = options["districts"]
        villages_path = options["villages"]

        for p in [provinces_path, regencies_path, districts_path, villages_path]:
            if not os.path.exists(p):
                raise CommandError(f"File tidak ditemukan: {p}")

        self.stdout.write(self.style.WARNING("Mulai import wilayah Indonesia (Kemendagri CSV)…"))

        with transaction.atomic():
            self._ensure_country()
            code_map = self._import_provinces(provinces_path)
            self._import_regencies(regencies_path, code_map)
            self._import_districts(districts_path, code_map)
            self._import_villages(villages_path, code_map)

        self.stdout.write(self.style.SUCCESS("Import wilayah Indonesia selesai tanpa error."))

    # ---------- Helpers dasar ----------

    def _ensure_country(self):
        country, created = Location.objects.get_or_create(
            code="ID",
            defaults=dict(
                name="Indonesia",
                kind="country",
                parent=None,
                country_code="ID",
                status="active",
                source="Kemendagri",
                display_name="Indonesia",
            ),
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Membuat lokasi negara Indonesia (ID)"))
        else:
            self.stdout.write(self.style.WARNING("Negara Indonesia (ID) sudah ada, dipakai sebagai root."))

    def _open_reader(self, path):
        """
        Buka CSV dan kembalikan (reader, normalized_headers_map)
        normalized_headers_map: dict key-normalized -> nama_asli_di_row
        """
        f = open(path, newline="", encoding="utf-8")
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            f.close()
            raise CommandError(f"File {path} tidak memiliki header.")

        # normalisasi: strip spasi & lower
        header_map = {}
        for h in reader.fieldnames:
            norm = h.strip().lower()
            header_map[norm] = h

        return f, reader, header_map

    # ---------- Import per level ----------

    def _import_provinces(self, path):
        """
        provinces.csv: code,name
        """
        self.stdout.write(self.style.WARNING(f"Import provinces dari {path}"))
        code_map = {}

        f, reader, headers = self._open_reader(path)

        required = {"code", "name"}
        if not required.issubset(headers.keys()):
            f.close()
            raise CommandError(
                f"Header provinces.csv minimal harus punya: {required}. "
                f"Header sekarang: {reader.fieldnames}"
            )

        country = Location.objects.get(code="ID")

        for row in reader:
            code = (row[headers["code"]] or "").strip()
            name = (row[headers["name"]] or "").strip()
            if not code or not name:
                continue

            obj, created = Location.objects.get_or_create(
                code=code,
                defaults=dict(
                    name=name,
                    kind="province",
                    parent=country,
                    country_code="ID",
                    status="active",
                    source="Kemendagri",
                    display_name=f"{name.title()} (Provinsi)",
                ),
            )
            if created:
                self.stdout.write(f"  + province {code} - {name}")
            else:
                self.stdout.write(f"  = province {code} - {name} (sudah ada, dilewati)")
            code_map[code] = obj

        f.close()
        return code_map

    def _import_regencies(self, path, code_map):
        """
        regencies.csv: code,province_id,name
        """
        self.stdout.write(self.style.WARNING(f"Import regencies dari {path}"))
        created_count = 0

        f, reader, headers = self._open_reader(path)

        required = {"code", "province_id", "name"}
        if not required.issubset(headers.keys()):
            f.close()
            raise CommandError(
                f"Header regencies.csv minimal harus punya: {required}. "
                f"Header sekarang: {reader.fieldnames}"
            )

        for row in reader:
            code = (row[headers["code"]] or "").strip()
            prov_code = (row[headers["province_id"]] or "").strip()
            name = (row[headers["name"]] or "").strip()
            if not code or not prov_code or not name:
                continue

            parent = code_map.get(prov_code)
            if not parent:
                f.close()
                raise CommandError(
                    f"Province dengan code={prov_code} belum diimport "
                    f"(regency {code} - {name})"
                )

            upper_name = name.upper()
            kind = "city" if upper_name.startswith("KOTA ") else "regency"

            obj, created = Location.objects.get_or_create(
                code=code,
                defaults=dict(
                    name=name,
                    kind=kind,
                    parent=parent,
                    country_code="ID",
                    status="active",
                    source="Kemendagri",
                    display_name=f"{name.title()}, {parent.name.title()}",
                ),
            )
            if created:
                created_count += 1
                code_map[code] = obj

        f.close()
        self.stdout.write(self.style.SUCCESS(f"Dibuat {created_count} regencies/cities."))

    def _import_districts(self, path, code_map):
        """
        districts.csv: code,regency_id,name
        """
        self.stdout.write(self.style.WARNING(f"Import districts dari {path}"))
        created_count = 0

        f, reader, headers = self._open_reader(path)

        required = {"code", "regency_id", "name"}
        if not required.issubset(headers.keys()):
            f.close()
            raise CommandError(
                f"Header districts.csv minimal harus punya: {required}. "
                f"Header sekarang: {reader.fieldnames}"
            )

        for row in reader:
            code = (row[headers["code"]] or "").strip()
            reg_code = (row[headers["regency_id"]] or "").strip()
            name = (row[headers["name"]] or "").strip()
            if not code or not reg_code or not name:
                continue

            parent = code_map.get(reg_code)
            if not parent:
                f.close()
                raise CommandError(
                    f"Regency/city dengan code={reg_code} belum diimport "
                    f"(district {code} - {name})"
                )

            obj, created = Location.objects.get_or_create(
                code=code,
                defaults=dict(
                    name=name,
                    kind="district",
                    parent=parent,
                    country_code="ID",
                    status="active",
                    source="Kemendagri",
                    display_name=f"Kec. {name.title()}, {parent.name.title()}",
                ),
            )
            if created:
                created_count += 1
                code_map[code] = obj

        f.close()
        self.stdout.write(self.style.SUCCESS(f"Dibuat {created_count} districts."))

    def _import_villages(self, path, code_map):
        """
        villages.csv: code,district_id,name
        """
        self.stdout.write(self.style.WARNING(f"Import villages dari {path}"))
        created_count = 0

        f, reader, headers = self._open_reader(path)

        required = {"code", "district_id", "name"}
        if not required.issubset(headers.keys()):
            f.close()
            raise CommandError(
                f"Header villages.csv minimal harus punya: {required}. "
                f"Header sekarang: {reader.fieldnames}"
            )

        for row in reader:
            code = (row[headers["code"]] or "").strip()
            dist_code = (row[headers["district_id"]] or "").strip()
            name = (row[headers["name"]] or "").strip()
            if not code or not dist_code or not name:
                continue

            parent = code_map.get(dist_code)
            if not parent:
                f.close()
                raise CommandError(
                    f"District dengan code={dist_code} belum diimport "
                    f"(village {code} - {name})"
                )

            obj, created = Location.objects.get_or_create(
                code=code,
                defaults=dict(
                    name=name,
                    kind="village",
                    parent=parent,
                    country_code="ID",
                    status="active",
                    source="Kemendagri",
                    display_name=f"{name.title()}, {parent.name.title()}",
                ),
            )
            if created:
                created_count += 1

        f.close()
        self.stdout.write(self.style.SUCCESS(f"Dibuat {created_count} villages."))
