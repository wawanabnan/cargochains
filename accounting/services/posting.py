from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from accounting.models.journal import Journal, JournalLine
from accounting.models.chart import Account
from accounting.services.periods import is_period_locked


def _d(v) -> Decimal:
    if v is None:
        return Decimal("0.00")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


@transaction.atomic
def create_journal(*, number: str, date, description: str = "", ref: str = "", lines: list[dict]) -> Journal:
    """
    lines item:
      {"account": Account|id, "debit": 100, "credit": 0, "label": "text"}
    """
    j = Journal.objects.create(number=number, date=date, description=description, ref=ref, posted=False)

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for ln in lines:
        acct = ln["account"]
        if isinstance(acct, int):
            acct = Account.objects.get(pk=acct)

        debit = _d(ln.get("debit"))
        credit = _d(ln.get("credit"))
        label = (ln.get("label") or "").strip()

        jl = JournalLine(journal=j, account=acct, debit=debit, credit=credit, label=label)
        jl.full_clean()
        jl.save()

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise ValidationError(f"Journal not balanced: debit={total_debit} credit={total_credit}")

    return j


@transaction.atomic
def post_journal(journal: Journal) -> Journal:
    """
    Set posted=True. Setelah posted, nanti UI kita lock.
    """

    
    # ✅ period lock
    if is_period_locked(journal.date):
        raise ValidationError(f"Period {journal.date:%Y-%m} is locked. Cannot post journal.")

    # ✅ must be balanced
    if journal.total_debit != journal.total_credit:
        raise ValidationError("Cannot post: journal not balanced.")


    journal.posted = True
    journal.full_clean()
    journal.save(update_fields=["posted"])
    return journal
