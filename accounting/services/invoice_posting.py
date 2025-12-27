from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.services.posting import create_journal, post_journal
from accounting.models.settings import AccountingSettings


@transaction.atomic
def create_journal_from_invoice(invoice):
    """
    Create & post journal for SALES INVOICE
    """

    # 1. Guard
    if invoice.journal_id:
        return invoice.journal  # idempotent

    if invoice.subtotal_amount is None:
        raise ValidationError("Invoice amount is empty.")

    settings = AccountingSettings.get_solo()

    ar = settings.default_ar_account
    revenue = settings.default_sales_account
    tax = settings.default_tax_account

    if not ar or not revenue:
        raise ValidationError("Accounting Settings belum lengkap (AR / Revenue).")

    lines = []

    # 2. Debit AR
    lines.append({
        "account": ar,
        "debit": invoice.total_amount,
        "credit": Decimal("0.00"),
        "label": f"Invoice {invoice.number}",
    })

    # 3. Credit Revenue
    lines.append({
        "account": revenue,
        "debit": Decimal("0.00"),
        "credit": invoice.subtotal_amount,
        "label": f"Invoice {invoice.number}",
    })

    # 4. Credit Tax (kalau ada)
    if invoice.tax_amount and invoice.tax_amount > 0:
        if not tax:
            raise ValidationError("Tax Payable account belum diset.")
        lines.append({
            "account": tax,
            "debit": Decimal("0.00"),
            "credit": invoice.tax_amount,
            "label": "Output Tax",
        })

    # 5. Create journal (BELUM POST)
    journal = create_journal(
        number="",  # auto dari next_journal_number()
        date=invoice.invoice_date,
        ref=invoice.number,
        description=f"Sales Invoice {invoice.number}",
        lines=lines,
    )

    # 6. POST journal (akan cek period lock + balance)
    post_journal(journal)

    # 7. Link balik ke invoice
    invoice.journal = journal
    invoice.save(update_fields=["journal"])

    return journal
