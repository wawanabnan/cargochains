from billing.models.config import BillingConfig
from accounting.models.config import AccountingConfig


def process_invoice_journal(invoice):

    billing_config = BillingConfig.get_solo()

    if billing_config.invoice_auto_mode == BillingConfig.AUTO_OFF:
        return None

    accounting_config = AccountingConfig.get_solo()

    journal = create_invoice_journal(
        invoice,
        journal=accounting_config.default_sales_journal
    )

    if billing_config.invoice_auto_mode == BillingConfig.AUTO_JOURNAL_POST:
        journal.post()

    return journal