from django.db import models
from decimal import Decimal
from django.conf import settings
from core.models.currencies import Currency
from django_summernote.fields import SummernoteTextField

class SignatureSource(models.TextChoices):
    SALES_USER = "SALES_USER", "Sales User"
    SPECIFIC_USER = "SPECIFIC_USER", "Specific User"


class SalesConfig(models.Model):
    """
    Global (single-row) sales config.
    """

    quotation_signature_source = models.CharField(
        max_length=20,
        choices=SignatureSource.choices,
        default=SignatureSource.SALES_USER,
    )

    quotation_signature_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Dipakai jika source = SPECIFIC_USER"
    )

    joborder_signature_source = models.CharField(
        max_length=20,
        choices=SignatureSource.choices,
        default=SignatureSource.SALES_USER,
    )

    joborder_signature_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Dipakai jika source = SPECIFIC_USER"
    )

    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Default currency untuk quotation / job order"
    )

    updated_at = models.DateTimeField(auto_now=True)


    quotation_valid_days = models.PositiveIntegerField(
        default=0,
        help_text="0 = tidak pakai masa berlaku (opsional).",
    )

    sales_fee_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Fee dalam persen, contoh: 2.50",
    )

    customer_note =  SummernoteTextField(blank=True, default="")
    term_conditions =  SummernoteTextField(blank=True, default="")

    vendor_note =  SummernoteTextField(blank=True, default="")
    service_order_term_conditions =  SummernoteTextField(blank=True, default="")
    
    service_order_signature_source = models.CharField(
        max_length=20,
        choices=SignatureSource.choices,
        default=SignatureSource.SALES_USER,
    )

    service_order_signature_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Dipakai jika source = SPECIFIC_USER"
    )


    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sales Config"
        verbose_name_plural = "Sales Config"

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        return obj if obj else cls.objects.create()
