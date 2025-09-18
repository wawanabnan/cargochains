from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps
from datetime import datetime

# ====== DATA ======
COUNTRY = "Indonesia"

CITIES = [
    "Jakarta","Surabaya","Bandung","Medan","Semarang","Makassar","Palembang","Tangerang",
    "Depok","Bekasi","Bogor","Malang","Yogyakarta","Denpasar","Balikpapan","Samarinda",
    "Pontianak","Banjarmasin","Pekanbaru","Batam","Padang","Banda Aceh","Manado","Ambon",
    "Jayapura","Kupang","Mataram","Palu","Kendari","Cirebon",
]

PORTS = [  # (name, city)
    ("Tanjung Priok", "Jakarta"),
    ("Tanjung Perak", "Surabaya"),
    ("Belawan", "Medan"),
    ("Tanjung Emas", "Semarang"),
    ("Soekarno-Hatta (Makassar)", "Makassar"),
    ("Teluk Bayur", "Padang"),
    ("Batu Ampar", "Batam"),
    ("Dwikora", "Pontianak"),
    ("Trisakti", "Banjarmasin"),
    ("Boom Baru", "Palembang"),
]

AIRPORTS = [  # (name, city)
    ("Soekarno–Hatta", "Tangerang"),
    ("Juanda", "Surabaya"),
    ("Kualanamu", "Medan"),
    ("Ahmad Yani", "Semarang"),
    ("Sultan Hasanuddin", "Makassar"),
    ("Ngurah Rai", "Denpasar"),
    ("Minangkabau", "Padang"),
    ("Sultan Syarif Kasim II", "Pekanbaru"),
    ("Sam Ratulangi", "Manado"),
    ("Supadio", "Pontianak"),
]

JETTIES = [  # (name, city)
    ("Pluit Jetty", "Jakarta"),
    ("Marunda Jetty", "Jakarta"),
    ("Paotere Jetty", "Makassar"),
    ("Kariangau Jetty", "Balikpapan"),
    ("Loa Janan Jetty", "Samarinda"),
    ("Kuin Jetty", "Banjarmasin"),
    ("Sungai Kakap Jetty", "Pontianak"),
    ("Cirebon Jetty", "Cirebon"),
    ("Tanjung Priok Coal Jetty", "Jakarta"),
    ("Tanjung Perak Bulk Jetty", "Surabaya"),
]


def get_location_model():
    # Coba beberapa nama app umum; ganti sesuai projekmu kalau perlu
    for app_label, model_name in [("geo", "Location"), ("locations", "Location")]:
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            continue
    raise LookupError("Tidak menemukan model Location (coba 'geo.Location').")

def field_exists(Model, name):
    return any(f.name == name for f in Model._meta.get_fields())

def set_if_exists(obj, **kwargs):
    for k, v in kwargs.items():
        if field_exists(obj.__class__, k):
            setattr(obj, k, v)


class Command(BaseCommand):
    help = "Seed geo locations (Indonesia): 30 cities, 10 ports, 10 airports, 10 jetties — with parent/child if supported."

    @transaction.atomic
    def handle(self, *args, **opts):
        Location = get_location_model()

        # Deteksi field opsional
        has_parent = field_exists(Location, "parent")
        type_field = "type" if field_exists(Location, "type") else (
            "kind" if field_exists(Location, "kind") else (
                "category" if field_exists(Location, "category") else None
            )
        )

        created, updated = 0, 0

        # Country
        country, was_created = Location.objects.get_or_create(name=COUNTRY)
        if type_field:
            set_if_exists(country, **{type_field: "country"})
            country.save(update_fields=[type_field])  # safe jika ada
        created += int(was_created); updated += int(not was_created)

        # Cities
        city_objects = {}
        for city in CITIES:
            defaults = {}
            if type_field:
                defaults[type_field] = "city"
            if has_parent:
                defaults["parent"] = country

            obj, was_created = Location.objects.get_or_create(name=city, defaults=defaults)
            if not was_created:
                # update ringan (jika field ada)
                if type_field and getattr(obj, type_field, None) != "city":
                    set_if_exists(obj, **{type_field: "city"})
                if has_parent and getattr(obj, "parent_id", None) != country.id:
                    obj.parent = country
                obj.save()
            city_objects[city] = obj
            created += int(was_created); updated += int(not was_created)

        # Helper create under city
        def create_child(name, city_name, label):
            parent = city_objects.get(city_name)
            defaults = {}
            if type_field:
                defaults[type_field] = label
            if has_parent and parent:
                defaults["parent"] = parent
            obj, was_created = Location.objects.get_or_create(name=name, defaults=defaults)
            if not was_created:
                need_save = False
                if type_field and getattr(obj, type_field, None) != label:
                    set_if_exists(obj, **{type_field: label})
                    need_save = True
                if has_parent and parent and getattr(obj, "parent_id", None) != parent.id:
                    obj.parent = parent; need_save = True
                if need_save:
                    obj.save()
            return was_created

        # Ports
        for name, city in PORTS:
            created += int(create_child(name, city, "port"))
        # Airports
        for name, city in AIRPORTS:
            created += int(create_child(name, city, "airport"))
        # Jetties
        for name, city in JETTIES:
            created += int(create_child(name, city, "jetty"))

        self.stdout.write(self.style.SUCCESS(
            f"Locations seeded. Created={created}, Updated={updated}. "
            f"(parent={'yes' if has_parent else 'no'}, type_field={type_field or '-'})"
        ))
