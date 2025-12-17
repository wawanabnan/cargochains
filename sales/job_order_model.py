from django.db import models
from django.db.models import PROTECT
from django.conf import settings
from django.db.models import Q

from core.models import TimeStampedModel, SalesService, PaymentTerm
from core.models import Currency, Service
from core.utils import get_next_number
from partners.models import Partner
from partners.models import Customer
from decimal import Decimal


class JobOrder(TimeStampedModel):
    """
    Jobfile untuk team sales.

    Satu baris = satu job penjualan, basisnya customer + service.
    """
    
    number = models.CharField("Job No", max_length=30, unique=True)
    order_number = models.CharField(
        max_length=30, 
        null=True,
        blank=True,
        help_text="Customer reference eg. PO#",
        
    )

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

    kurs_idr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
    )

    total_in_idr = models.DecimalField(
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


    is_invoiced = models.BooleanField(
        default=False,
        help_text="Sudah dibuat invoice"
    )

    class Meta:
        db_table = "sales_job_orders"
        ordering = ["-job_date", "-id"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            # Pakai NumberSequence: app='sales', code='JOBFILE'
            self.number = get_next_number("sales", "JOB_ORDER")
        super().save(*args, **kwargs)



class JobCost(models.Model):
    job_order = models.ForeignKey(
        JobOrder,
        on_delete=models.CASCADE,
        related_name="costs",
        db_index=True
    )

    description = models.CharField(max_length=255)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sales_job_costs"
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} ({self.amount})"

    def save(self, *args, **kwargs):
        # hitung amount otomatis
        self.amount = (self.qty or Decimal("0")) * (self.price or Decimal("0"))
        super().save(*args, **kwargs)



class JobOrderAttachment(TimeStampedModel):
    job_order = models.ForeignKey(
        "JobOrder",
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Job Order",
    )
    file = models.FileField(
        upload_to="job_orders/%Y/%m/",
        verbose_name="File",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Description",
        help_text="Keterangan singkat file, misal: PO Customer, Kontrak, dll."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="joborder_attachments",
    )

    class Meta:
        verbose_name = "Job Order Attachment"
        verbose_name_plural = "Job Order Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_order.number} - {self.filename}"

    @property
    def filename(self):
        return self.file.name.split("/")[-1]
