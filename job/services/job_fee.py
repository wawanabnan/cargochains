from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from django.db import transaction
from django.utils import timezone

from job.models.job_orders import JobOrder, 
from job.models.job_fee import JobFeeLine,JobFeePeriod,JobFeePeriodStatus

TWO = Decimal("0.01")


def month_start(d: date) -> date:
    return d.replace(day=1)


def next_month_start(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


@transaction.atomic
def generate_job_fee_for_month(
    month: date,
    percent: Decimal,
    *,
    user=None,
    replace_if_draft: bool = True,
):
    """
    Generate Sales Fee berdasarkan JobOrder yang status='completed' pada bulan completed_at.
    Bulan tanpa job completed => period tidak dibuat (report tidak muncul).
    """
    m0 = month_start(month)
    m1 = next_month_start(m0)

    period = JobFeePeriod.objects.filter(month=m0).first()
    created = False

    if period:
        # kalau sudah approved/paid, jangan regenerate
        if period.status != JobFeePeriodStatus.DRAFT:
            return period, 0

        if replace_if_draft:
            period.lines.all().delete()

        period.percent = percent
    else:
        period = JobFeePeriod(month=m0, percent=percent)
        created = True

    qs = JobOrder.objects.filter(
        status="completed",
        completed_at__gte=m0,
        completed_at__lt=m1,
    ).select_related("sales_user")

    # bulan kosong => period tidak dibuat
    if not qs.exists():
        if not created:
            period.delete()
        return None, 0

    period.generated_at = timezone.now()
    period.generated_by = user if getattr(user, "pk", None) else None
    period.save()

    pct = Decimal(percent).quantize(TWO, rounding=ROUND_HALF_UP)

    n = 0
    for jo in qs:
        base = Decimal(jo.total_amount or 0).quantize(TWO, rounding=ROUND_HALF_UP)
        fee = (base * pct / Decimal("100")).quantize(TWO, rounding=ROUND_HALF_UP)

        JobFeeLine.objects.create(
            period=period,
            job_order=jo,
            sales_user=jo.sales_user,
            base_amount=base,
            percent=pct,
            fee_amount=fee,
        )
        n += 1

    period.recalc_totals()
    period.save(update_fields=["total_base_amount", "total_fee_amount", "percent", "generated_at", "generated_by"])

    return period, n
