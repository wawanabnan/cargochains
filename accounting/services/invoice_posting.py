from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.services.posting import create_journal, post_journal
from accounting.models.settings import AccountingSettings

from decimal import Decimal
from django.core.exceptions import ValidationError



def _invoice_amounts_base_idr(invoice):
    """
    Return tuple: (total_base, subtotal_base, tax_base)
    Base currency = IDR (Chart of Account)

    Rules:
    - IDR invoice  -> pakai amount asli
    - Non-IDR     -> pakai amount IDR (total_idr) + konversi dari rate
    """

    code = (getattr(invoice.currency, "code", "") or "").upper()
    rate = getattr(invoice, "exchange_rate", None) or Decimal("1.0")

    if code == "IDR" or not code:
        total_base = invoice.total_amount
        subtotal_base = invoice.subtotal_amount
        tax_base = invoice.tax_amount or Decimal("0.00")
    else:
        # wajib sudah lock FX saat confirm
        total_base = getattr(invoice, "total_idr", None)
        if total_base is None:
            raise ValidationError(
                "⚠️ total_idr belum tersedia.\n"
                "Invoice non-IDR harus dikonfirmasi (lock FX) sebelum membuat journal."
            )

        subtotal_base = (invoice.subtotal_amount or Decimal("0.00")) * rate
        tax_base = (invoice.tax_amount or Decimal("0.00")) * rate

    return total_base, subtotal_base, tax_base


def _pick_invoice_service(invoice):
    # 1) dari invoice line.service (kalau ada)
    try:
        line = invoice.lines.select_related("service").order_by("id").first()
        if line and getattr(line, "service", None):
            return line.service
    except Exception:
        pass

    # 2) fallback dari job_order
    if getattr(invoice, "job_order_id", None):
        jo = invoice.job_order
        return getattr(jo, "sales_service", None) or getattr(jo, "service", None)

    return None


@transaction.atomic
def create_journal_from_invoice(invoice):
    """
    STRICT:
    - Journal accounts MUST come from Service (Receivable & Revenue).
    - If mapping missing -> raise ValidationError (friendly) -> caller must rollback confirm.
    """

    if invoice.journal_id:
        return invoice.journal  # idempotent

    if invoice.total_amount is None or invoice.subtotal_amount is None:
        raise ValidationError(
            "⚠️ Tidak bisa membuat journal karena nilai invoice kosong.\n"
            "Pastikan subtotal/total sudah terisi sebelum confirm."
        )

    svc = _pick_invoice_service(invoice)
    if not svc:
        raise ValidationError(
            "⚠️ Tidak bisa membuat journal karena Service tidak terdeteksi.\n"
            "Pastikan invoice line memiliki Service, atau Job Order memiliki Service."
        )

    ar = getattr(svc, "receivable_account", None)
    revenue = getattr(svc, "revenue_account", None)

    if not ar or not revenue:
        raise ValidationError(
            "⚠️ Mapping akun untuk Service belum tersedia.\n\n"
            f"Service: {getattr(svc, 'name', '(unknown)')}\n\n"
            "Silakan isi:\n"
            "- Receivable Account (AR)\n"
            "- Revenue Account\n\n"
            "atau hubungi Akuntan Anda.\n\n"
            "Proses dibatalkan: Invoice tidak berubah dan journal tidak dibuat."
        )

    acc = AccountingSettings.get_solo()
    tax = getattr(acc, "default_tax_account", None)

    lines_old = [
        {"account": ar, "debit": invoice.total_amount, "credit": Decimal("0.00"), "label": f"Invoice {invoice.number}"},
        {"account": revenue, "debit": Decimal("0.00"), "credit": invoice.subtotal_amount, "label": f"Invoice {invoice.number}"},
    ]

    total_base, sub_base, tax_base = _invoice_amounts_base_idr(invoice)

    lines = [
        {
            "account": ar,
            "debit": total_base,
            "credit": Decimal("0.00"),
            "label": f"Invoice {invoice.number}",
        },
        {
            "account": revenue,
            "debit": Decimal("0.00"),
            "credit": sub_base,
            "label": f"Invoice {invoice.number}",
        },
    ]

    if tax_base and tax_base > 0:
        if not tax:
            raise ValidationError(
                "⚠️ Invoice memiliki Tax, tapi Default Tax Account belum diset.\n"
                "Silakan isi di Accounting Settings → Default Tax Account.\n\n"
                "Proses dibatalkan: Invoice tidak berubah dan journal tidak dibuat."
            )
        lines.append(
            {
                "account": tax,
                "debit": Decimal("0.00"),
                "credit": tax_base,
                "label": "Output Tax",
            }
    )

    if invoice.tax_amount and invoice.tax_amount > 0:
        if not tax:
            raise ValidationError(
                "⚠️ Invoice memiliki Tax, tapi Default Tax Account belum diset.\n"
                "Silakan isi di Accounting Settings → Default Tax Account.\n\n"
                "Proses dibatalkan: Invoice tidak berubah dan journal tidak dibuat."
            )
        lines.append({"account": tax, "debit": Decimal("0.00"), "credit": invoice.tax_amount, "label": "Output Tax"})

    journal = create_journal(
        number="",
        date=invoice.invoice_date,
        ref=invoice.number,
        description=f"Sales Invoice {invoice.number}",
        lines=lines,
    )

    post_journal(journal)

    invoice.journal = journal
    invoice.save(update_fields=["journal"])

    return journal



