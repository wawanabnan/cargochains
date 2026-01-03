# job/services/posting.py

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from accounting.models.journal import Journal,JournalLine
from accounting.models.settings import AccountingSettings


def ensure_job_costing_posted(job):
    """
    Auto post COGS accrual for job costing (ACCRUAL BASIS).
    Dipanggil SETIAP job COMPLETE.
    Idempotent (tidak bisa dobel posting).
    """

    settings = AccountingSettings.get_solo()
    if not settings.auto_post_job_costing:
        return

    # anti dobel posting (by source_ref)
    if Journal.objects.filter(
        source_type="JOB",
        source_ref=job.number,
    ).exists():
        return

    # ✅ ACCRUAL: pakai ESTIMATE (est_amount), bukan actual
    costs = job.job_costs.filter(is_active=True).exclude(est_amount__isnull=True)

    # total estimate = 0 → skip posting
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
