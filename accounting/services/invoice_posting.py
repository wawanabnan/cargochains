from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.services.posting import create_journal, post_journal
from accounting.models.settings import AccountingSettings

from decimal import Decimal
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.models.settings import AccountingSettings
from accounting.services.posting import create_journal, post_journal  # sesuaikan import om


D0 = Decimal("0.00")


@transaction.atomic
def create_journal_from_invoice(invoice):
    """
    UPDATED RULES:
    - Jika Service terdeteksi & mapping lengkap -> pakai mapping Service (AR & Revenue).
    - Jika Service tidak ada / mapping kurang -> fallback ke AccountingSettings:
        - default_ar_account
        - default_sales_account
    - Tax -> AccountingSettings.default_tax_account (wajib jika invoice punya tax).
    """

    if invoice.journal_id:
        return invoice.journal  # idempotent

    if invoice.total_amount is None or invoice.subtotal_amount is None:
        raise ValidationError(
            "⚠️ Tidak bisa membuat journal karena nilai invoice kosong.\n"
            "Pastikan subtotal/total sudah terisi sebelum confirm."
        )

    # ✅ ambil settings sekali
    acc = AccountingSettings.get_solo()

    # 1) coba ambil dari service (line/job)
    svc = _pick_invoice_service(invoice)

    ar = revenue = None
    used_fallback = False

    if svc:
        ar = getattr(svc, "receivable_account", None)
        revenue = getattr(svc, "revenue_account", None)

    # 2) fallback ke default accounts kalau service tidak ada / mapping kurang
    if not ar or not revenue:
        fb_ar = getattr(acc, "default_ar_account", None)
        fb_rev = getattr(acc, "default_sales_account", None)

        if not fb_ar or not fb_rev:
            raise ValidationError(
                "⚠️ Tidak bisa membuat journal karena Service tidak terdeteksi / mapping Service belum lengkap,\n"
                "dan Default Accounts untuk Sales Invoice belum diset.\n\n"
                "Silakan isi di Accounting Settings:\n"
                "- Default Accounts Receivable (AR)\n"
                "- Default Sales Revenue\n\n"
                "Atau isi Service pada invoice line."
            )

        ar = ar or fb_ar
        revenue = revenue or fb_rev
        used_fallback = True

    tax = getattr(acc, "default_tax_account", None)

    # label audit
    label_suffix = " (DEFAULT SALES)" if used_fallback else ""
    label = f"Invoice {invoice.number}{label_suffix}"

    # journal lines
    lines = [
        {
            "account": ar,
            "debit": invoice.total_amount,
            "credit": D0,
            "label": label,
        },
        {
            "account": revenue,
            "debit": D0,
            "credit": invoice.subtotal_amount,
            "label": label,
        },
    ]

    if invoice.tax_amount and invoice.tax_amount > 0:
        if not tax:
            raise ValidationError(
                "⚠️ Invoice memiliki Tax, tapi Default Tax Account belum diset.\n"
                "Silakan isi di Accounting Settings → Default Tax Account.\n\n"
                "Proses dibatalkan: Invoice tidak berubah dan journal tidak dibuat."
            )
        lines.append(
            {"account": tax, "debit": D0, "credit": invoice.tax_amount, "label": "Output Tax"}
        )

    # create + post journal
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
