from django.db import models
from django.db.models import PROTECT
from django.conf import settings
from django.db.models import Q

from core.models import TimeStampedModel, SalesService, PaymentTerm
from core.models import Currency, Service
from core.utils import get_next_number
from partners.models import Partner
from partners.models import Customer


class JobOrder(TimeStampedModel):
    """
    Jobfile untuk team sales.

    Satu baris = satu job penjualan, basisnya customer + service.
    """
    number = models.CharField("Job No", max_length=30, unique=True)
    job_date = models.DateField("Date")

    service = models.ForeignKey(
        Service,
        on_delete=PROTECT,
        related_name="job_services",
        verbose_name="Service",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=PROTECT,
        related_name="customer_job",
        verbose_name="Customer",
        
    )

    cargo_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Deskripsi singkat cargo.",
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Jumlah / volume cargo (opsional).",
    )

    pickup = models.CharField(
        "Pick Up",
        max_length=255,
        blank=True,
        help_text="Alamat / lokasi penjemputan.",
    )

    delivery = models.CharField(
        "Delivery",
        max_length=255,
        blank=True,
        help_text="Alamat / lokasi pengantaran.",
    )

    pic = models.CharField(
        "PIC",
        max_length=100,
        blank=True,
        help_text="Nama PIC.",
    )

    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=PROTECT,
        related_name="job_payments",
        verbose_name="Payment Term",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=PROTECT,
        default=1,  # sesuaikan default ID om
    )


    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )


    is_tax = models.BooleanField(default=False, verbose_name="Apply Tax 1.1 (VAT)")
    is_pph = models.BooleanField(default=False, verbose_name="Apply PPH")

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    pph_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    pph_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    grand_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )


    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        related_name="job_sales",
        verbose_name="Sales",
        null=True,
        blank=True,
        
    )


    remarks_internal = models.TextField(
        blank=True,
        help_text="Catatan internal untuk tim.",
    )

    class Meta:
        ordering = ["-job_date", "-id"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            # Pakai NumberSequence: app='sales', code='JOBFILE'
            self.number = get_next_number("sales", "JOB")
        super().save(*args, **kwargs)
