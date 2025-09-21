from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from sales.models import (
    SalesQuotation, SalesQuotationLine,
    SalesService, Currency, PaymentTerm, UOM
)
from partners.models import Partner
from geo.models import Location

class Command(BaseCommand):
    help = "Seed dummy SalesQuotation + lines (idempotent & supports flush/overwrite)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=10, help="How many quotations to create")
        parser.add_argument("--start", type=int, default=1, help="Start index (e.g. 1 produces 0001)")
        parser.add_argument("--prefix", default="QO-2025-", help="Quotation number prefix")
        parser.add_argument("--flush", action="store_true", help="Delete ALL existing quotations before seeding")
        parser.add_argument("--overwrite", action="store_true", help="Delete existing quote with same number before re-creating")

    def handle(self, *args, **opt):
        count = opt["count"]
        start = opt["start"]
        prefix = opt["prefix"]
        flush = opt["flush"]
        overwrite = opt["overwrite"]

        # Basic FKs
        customers = list(Partner.objects.filter(id__in=[7, 8, 9, 10]))
        service = SalesService.objects.first()
        currency = Currency.objects.first()
        term = PaymentTerm.objects.first()
        uom = UOM.objects.first()
        origin = Location.objects.first()
        dest = Location.objects.last()

        if not customers or not all([service, currency, term, uom, origin, dest]):
            self.stderr.write(self.style.ERROR("Missing base data (customers 7-10, service, currency, term, uom, location)."))
            return

        if flush:
            # Hapus header & lines (cascade akan urus lines kalau FK CASCADE)
            SalesQuotation.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed all SalesQuotation data."))

        created = 0
        skipped = 0
        updated = 0

        for i in range(start, start + count):
            number = f"{prefix}{i:04d}"

            # handle overwrite / skip
            existing = SalesQuotation.objects.filter(number=number).first()
            if existing and overwrite:
                existing.delete()
                existing = None
                self.stdout.write(self.style.WARNING(f"Overwrote existing {number}"))

            if existing:
                skipped += 1
                self.stdout.write(f"Skip (exists): {number}")
                continue

            with transaction.atomic():
                q = SalesQuotation.objects.create(
                    number=number,
                    customer=customers[(i - start) % len(customers)],
                    sales_service=service,
                    currency=currency,
                    payment_term=term,
                    date=timezone.now().date(),
                    valid_until=timezone.now().date(),
                    status=SalesQuotation.STATUS_DRAFT,
                    business_type="freight",
                    total_amount=Decimal("0.00"),
                )

                # 1 line contoh
                SalesQuotationLine.objects.create(
                    sales_quotation=q,
                    origin=origin,
                    destination=dest,
                    description=f"Cargo {i}",
                    uom=uom,
                    qty=Decimal("10.00"),
                    price=Decimal("100.00"),
                    amount=Decimal("1000.00"),
                )

                q.recalc_totals()
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created {q.number} (total={q.total_amount})"))

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, skipped={skipped}, updated={updated}"))
