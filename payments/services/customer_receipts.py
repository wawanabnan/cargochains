from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from accounting.models.settings import AccountingSettings
from accounting.services.posting import create_journal, post_journal
from payments.models.customer_receipt import CustomerReceipt



def next_receipt_no():
    today = timezone.now().date()
    prefix = f"RCPT-{today:%Y%m}-"
    last = CustomerReceipt.objects.filter(receipt_no__startswith=prefix).order_by("-receipt_no").first()
    if not last or not last.receipt_no:
        return prefix + "0001"
    n = int(last.receipt_no.split("-")[-1])
    return prefix + f"{n+1:04d}"


@transaction.atomic
def post_receipt(rcpt: CustomerReceipt):
    if not rcpt.can_post:
        return rcpt.journal

    if rcpt.amount is None or rcpt.amount <= 0:
        raise ValidationError("Amount received harus > 0.")

    inv = rcpt.invoice
    settings = AccountingSettings.get_solo()

    ar = settings.default_ar_account
    cash = rcpt.cash_account or settings.default_cash_account
    pph_acc = settings.default_pph_account

    if not ar:
        raise ValidationError("Set Default AR Account di Accounting Configuration.")
    if not cash:
        raise ValidationError("Set Default Cash/Bank Account di Accounting Configuration atau pilih di CustomerReceipt.")

    pph = rcpt.pph_withheld or Decimal("0.00")
    if pph < 0:
        raise ValidationError("PPH tidak boleh negatif.")

    settlement = (rcpt.amount or Decimal("0.00")) + pph

    # guard outstanding
    outstanding = inv.outstanding_amount
    if settlement > outstanding:
        raise ValidationError(f"Total settlement (amount+pph) melebihi outstanding invoice. Outstanding={outstanding}")

    # jika ada pph, wajib mapping akunnya
    if pph > 0 and not pph_acc:
        raise ValidationError("PPH account belum diset. Set Default PPH Account di Accounting Configuration.")

    # numbering receipt (kalau belum ada)
    if not rcpt.receipt_no:
        rcpt.receipt_no = next_receipt_no()

    # journal lines
    lines = [
        {"account": cash, "debit": rcpt.amount, "credit": Decimal("0.00"), "label": f"CustomerReceipt {rcpt.receipt_no}"},
    ]
    if pph > 0:
        lines.append({"account": pph_acc, "debit": pph, "credit": Decimal("0.00"), "label": "PPH Withheld"})

    lines.append({"account": ar, "debit": Decimal("0.00"), "credit": settlement, "label": f"Payment for {inv.number}"})

    j = create_journal(
        number="",
        date=rcpt.receipt_date,
        ref=rcpt.receipt_no,
        description=f"CustomerReceipt {rcpt.receipt_no} for Invoice {inv.number}",
        lines=lines,
    )
    post_journal(j)

    # mark posted
    rcpt.journal = j
    rcpt.status = CustomerReceipt.ST_POSTED
    rcpt.save(update_fields=["receipt_no", "journal", "status"])

    # update invoice payment
    inv.amount_paid = (inv.amount_paid or Decimal("0.00")) + settlement
    if inv.outstanding_amount <= Decimal("0.00"):
        inv.status = inv.ST_PAID
        inv.save(update_fields=["amount_paid", "status"])
    else:
        inv.save(update_fields=["amount_paid"])

    return j
