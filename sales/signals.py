# sales/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SalesQuotationLine

def _recalc_header(instance):
    header = instance.sales_quotation
    if header_id := getattr(header, "id", None):
        header.recalc_totals()

@receiver(post_save, sender=SalesQuotationLine)
def _line_saved(sender, instance, **kwargs):
    _recalc_header(instance)

@receiver(post_delete, sender=SalesQuotationLine)
def _line_deleted(sender, instance, **kwargs):
    _recalc_header(instance)
