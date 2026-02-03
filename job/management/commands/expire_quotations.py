from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from quotations.models import Quotation, QuotationStatus


class Command(BaseCommand):
    help = "Mark quotations as EXPIRED when valid_until has passed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many would be updated, without updating",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        dry_run = options["dry_run"]

        # Kandidat expired: valid_until < today, masih aktif (DRAFT/SENT)
        qs = (
            Quotation.objects.select_for_update()
            .filter(valid_until__lt=today, status__in=[QuotationStatus.DRAFT, QuotationStatus.SENT])
        )

        count = qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would expire: {count} quotation(s)."))
            return

        updated = qs.update(
            status=QuotationStatus.EXPIRED,
            expired_at=timezone.now(),
            expired_by_system=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Expired quotations updated: {updated} (candidates: {count})"))
