from types import SimpleNamespace
from django import template
from sales.policies.invoices import InvoicePolicy

register = template.Library()

@register.simple_tag
def cando(invoice, user):
    """
    Return object with booleans:
    abilities.can_confirm, abilities.can_edit, abilities.can_receive_payment
    """
    return SimpleNamespace(
        can_confirm=InvoicePolicy.can_confirm(invoice, user),
        can_edit=InvoicePolicy.can_edit(invoice, user),
        can_receive_payment=InvoicePolicy.can_receive_payment(invoice, user),
    )
