from django.db import models
from django.db.models import PROTECT
from django.conf import settings
from django.db.models import Q

from core.models.services import Service
from core.models.currencies import Currency
from core.models.payment_terms import  PaymentTerm
from core.models.taxes import  Tax


from core.utils.numbering import get_next_number
from partners.models import Partner
from partners.models import Customer
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JobOrder(TimeStampedModel):
    
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
        related_name="jobs_services",
        verbose_name="Service",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=PROTECT,
        related_name="customer_jobs",
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
        related_name="jobs_payments",
        verbose_name="Payment Term",
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=PROTECT,
        default=1,  # sesuaikan default ID om
         related_name="job_order_currency",
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
        related_name="job_order_sales_user",
       
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

    ST_DRAFT = "DRAFT"
    ST_IN_PROGRESS= "IN_PROGRESS"
    ST_ON_HOLD = "ON_HOLD"
    ST_CANCELLED = "CANCELLED"
    ST_COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (ST_DRAFT, "Draft"),
        (ST_IN_PROGRESS, "In Progress"),
        (ST_ON_HOLD, "On Hold"),
        (ST_CANCELLED, "Cancelled"),
        (ST_COMPLETED, "Completed"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ST_DRAFT,
        db_index=True,
    )

    # audit transisi
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        null=True, blank=True, related_name="+"
    )

    hold_at = models.DateTimeField(null=True, blank=True)
    hold_reason = models.CharField(max_length=255, blank=True, null=True), 

    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        null=True, blank=True, related_name="+"
    )

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        null=True, blank=True, related_name="+"
    )
    cancel_reason = models.CharField(max_length=255, blank=True, null=True)

    
    STATUS_COLORS = {
        ST_DRAFT: "secondary",
        ST_IN_PROGRESS: "info",
        ST_ON_HOLD: "warning",
        ST_COMPLETED: "success",
        ST_CANCELLED: "danger",
    }

    
    @property
    def job_status_label(self):
        color = self.STATUS_COLORS.get(self.status, "secondary")
        label = self.get_status_display()
        return mark_safe(
            f'<span class="badge text-bg-{color}">{label}</span>'
        )
    
    
    # --- helpers transisi (opsional tapi saya rekomendasikan) ---
    def can_confirm(self):
        return self.status == self.ST_DRAFT

    def confirm(self, user):
        if not self.can_confirm():
            raise ValueError("Job is not in DRAFT.")
        self.status = self.ST_IN_PROGRESS
        self.confirmed_at = timezone.now()
        self.confirmed_by = user

        # reset hold data (just in case)
        self.hold_at = None
        self.hold_reason = ""

    def can_hold(self):
        return self.status == self.ST_IN_PROGRESS

    def hold(self, user, reason: str):
        if not self.can_hold():
            raise ValueError("Job is not IN_PROGRESS.")
        if not (reason or "").strip():
            raise ValueError("Hold reason is required.")
        self.status = self.ST_ON_HOLD
        self.hold_at = timezone.now()
        self.hold_reason = reason.strip()

    def can_resume(self):
        return self.status == self.ST_ON_HOLD

    def resume(self, user):
        if not self.can_resume():
            raise ValueError("Job is not ON_HOLD.")
        self.status = self.ST_IN_PROGRESS

    def can_complete(self):
        return self.status == self.ST_IN_PROGRESS

    def can_cancel(self):
        # cancel boleh dari draft/ongoing/hold,
        # tapi kalau sudah posted journal, nanti kita bikin fitur reversal (jangan cancel langsung)
        return self.status in {self.ST_DRAFT, self.ST_IN_PROGRESS, self.ST_ON_HOLD} 

    def cancel(self, user, reason: str):
        if not self.can_cancel():
            raise ValueError("Job cannot be cancelled (maybe already posted).")
        if not (reason or "").strip():
            raise ValueError("Cancel reason is required.")
        self.status = self.ST_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancel_reason = reason.strip()

    def complete(self, user):
    # 1️⃣ hanya boleh complete dari IN_PROGRESS
        if self.status != self.ST_IN_PROGRESS:
            raise ValidationError("Job hanya bisa di-complete dari status In Progress.")

        costs = self.job_costs.filter(is_active=True)

        # ✅ Accrual basis:
        # - actual_amount TIDAK wajib saat complete
        # - boleh complete walau estimate kosong? (pilih salah satu)

        # Opsi A (tetap wajib ada cost line, tapi tidak wajib estimate > 0)
        if not costs.exists():
            raise ValidationError("Tidak bisa Complete: belum ada job cost.")

        # Opsi B (opsional disiplin: minimal ada estimate > 0)
        # if not costs.filter(est_amount__gt=0).exists():
        #     raise ValidationError("Tidak bisa Complete: Estimate Amount belum diisi.")

        # 3️⃣ update status (set dulu supaya posting bisa pakai completed_at)
        self.status = self.ST_COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save(update_fields=["status", "completed_at", "completed_by"])

        # 4️⃣ HOOK AUTO POSTING COGS (idempotent di service)
        from job.services.posting import ensure_job_costing_posted
        ensure_job_costing_posted(self)



    class Meta:
      
        ordering = ["-job_date", "-id"]
        db_table = "job_orders"
        verbose_name = "JobOrder"
        verbose_name_plural = "JobOrders"

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.pk and not self.number:
            # Pakai NumberSequence: app='sales', code='JOBFILE'
            self.number = get_next_number("job", "JOB_ORDER")
        super().save(*args, **kwargs)

    
class JobOrderAttachment(TimeStampedModel):
    job_order = models.ForeignKey(
        "JobOrder",
        on_delete=models.CASCADE,
        related_name="job_order_attachments",
        verbose_name="Job Order Attachment",
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
        related_name="job_order_user_attachments",
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
