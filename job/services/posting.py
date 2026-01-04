from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from accounting.models.settings import AccountingSettings
from accounting.models.journal import Journal, JournalLine


def ensure_job_costing_posted(job, *, user=None):
    """
    Job Costing Journal (COGS accrual estimate).
    Dipanggil SETIAP job COMPLETE.
    Idempotent: tidak create journal dobel untuk job yang sama.
    Opsi B:
      - auto_create_job_costing_journal: create journal draft
      - auto_post_job_costing_journal: post journal (lock)
    """

    settings = AccountingSettings.get_solo()

    # ✅ Opsi B: jika auto-create OFF, stop (tidak buat journal sama sekali)
    if not settings.auto_create_job_costing_journal:
        return

    # ✅ anti dobel (by source_ref) + backfill FK job.complete_journal
    existing = Journal.objects.filter(
        source_type="JOB",
        source_ref=job.number,
    ).first()

    if existing:
        if getattr(job, "complete_journal_id", None) != existing.id:
            job.complete_journal_id = existing.id
            job.save(update_fields=["complete_journal"])
        return

    # ✅ ACCRUAL: pakai ESTIMATE (est_amount), bukan actual
    costs = job.job_costs.filter(is_active=True).exclude(est_amount__isnull=True)

    if not costs.exists():
        return

    cogs_map = {}  # account_id -> amount

    for cost in costs:
        amt = cost.est_amount or Decimal("0")
        if amt <= 0:
            continue

        ct = cost.cost_type
        if not ct.cogs_account:
            raise ValidationError(
                f"Cost Type '{ct.name}' belum punya mapping COGS account"
            )

        acc_id = ct.cogs_account_id
        cogs_map.setdefault(acc_id, Decimal("0"))
        cogs_map[acc_id] += amt

    total_amount = sum(cogs_map.values(), Decimal("0"))
    if total_amount <= 0:
        return

    accrued = settings.default_accrued_cogs_account
    if not accrued:
        raise ValidationError("Default accrued account belum diset di Core Settings")

    with transaction.atomic():
        journal = Journal.objects.create(
            date=job.completed_at.date(),
            description=f"COGS (Accrual-Estimate) Job {job.number}",
            source_type="JOB",
            source_ref=job.number,
            currency=job.currency,
            created_by=user,
        )

        # Dr COGS (per cost type mapping)
        for acc_id, amount in cogs_map.items():
            JournalLine.objects.create(
                journal=journal,
                account_id=acc_id,
                debit=amount,
                credit=0,
            )

        # Cr Accrued
        JournalLine.objects.create(
            journal=journal,
            account=accrued,
            debit=0,
            credit=total_amount,
        )

        # ✅ link balik ke job supaya complete() bisa blok repeat
        job.complete_journal = journal
        job.save(update_fields=["complete_journal"])

        # ✅ Opsi B: auto-post hanya jika flag ini ON
        if settings.auto_post_job_costing_journal:
            from accounting.services.posting import post_journal  # local import anti circular
            post_journal(journal, user=user)
