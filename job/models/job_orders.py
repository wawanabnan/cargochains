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
from geo.models import Location
from django.db import transaction
from django.utils import formats
from django_summernote.fields import SummernoteTextField
from django.db.models import Sum

class JobOrderQuerySet(models.QuerySet):
    def visible(self):
        return self.exclude(status="QUOTATION")
    
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JobOrder(TimeStampedModel):

    objects = JobOrderQuerySet.as_manager()          # default
    all_objects = models.Manager()       
    
    number = models.CharField("Job No", max_length=30, unique=True)
    order_number = models.CharField(
        max_length=30, 
        null=True,
        blank=True,
        help_text="Customer reference eg. PO#",
        
    )

    job_date = models.DateField("Date")
    shp_date = models.DateField("Date",blank=True,null=True)

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

    origin = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="job_orders_origin",
    )
    destination = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="job_orders_destination",
    )

    shipper_name = models.CharField(max_length=255, blank=True)
    consignee_name = models.CharField(max_length=255, blank=True)
    

    cargo_description = models.TextField( 
        blank=True,
        help_text="Goods or matrials description.",
    )
    cargo_dimension = models.TextField( 
        blank=True,
        help_text="Goods or matrial package and dimensions",
    )
    customer_note = SummernoteTextField(
       
        blank=True,
        verbose_name="Customer Notes",
        help_text="Type your attension for your customer"
    )
    sla_note = models.TextField(
       
        blank=True,
        verbose_name="Description",
        help_text="Types your service level agreements."
    )

    term_conditions = SummernoteTextField(blank=True)
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Jumlah / volume cargo (opsional).",
    )

    pickup = models.TextField(
        "Pick Up",
        blank=True,
        help_text="Alamat / lokasi penjemputan.",
    )

    delivery = models.TextField(
        "Delivery",
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

    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    taxes = models.ManyToManyField(
        Tax,
        blank=True,
        related_name="job_taxes",
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

    down_payment_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_proforma = models.BooleanField(default=False)
    pph_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
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

    ST_QUOTATION = "QUOTATION"  
    ST_DRAFT = "DRAFT"
    ST_IN_COSTING = "IN_COSTING"
    ST_IN_PROGRESS= "IN_PROGRESS"
    ST_ON_HOLD = "ON_HOLD"
    ST_CANCELLED = "CANCELLED"
    ST_COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (ST_QUOTATION, "Quotation"),
        (ST_DRAFT, "Draft"),
        (ST_IN_COSTING, "In Costing"),
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

    # DISCOUNT
    DISCOUNT_TYPE_CHOICES = [
        ("PERCENT", "Percent"),
        ("AMOUNT", "Fixed Amount"),
    ]
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default="PERCENT",
    )

    discount_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    discount_notes = models.TextField(blank=True, default="")

    class JobSource(models.TextChoices):
      
        CUSTOMER_PO = "CUSTOMER_PO", "Customer PO"
        EMAIL = "EMAIL", "Email"

    job_source = models.CharField(
        max_length=20,
        choices=JobSource.choices,
        null=True,
        blank=True
    )
    
    bank_transfer_info = models.TextField(
        null=True,
        blank=True
    )
    

    # audit transisi
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=PROTECT,
        null=True, blank=True, related_name="+"
    )

    hold_at = models.DateTimeField(null=True, blank=True)
    hold_reason = models.CharField(max_length=255, blank=True, null=True)

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

    complete_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    

    STATUS_COLORS = {
        ST_DRAFT: "secondary",
        ST_IN_COSTING: "primary",
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
    
    @property
    def job_status_label_print (self):
        label = self.get_status_display()
        return mark_safe(
            f'<span class="label-print">{label}</span>'
        )
    
    @property
    def is_cost_locked(self):
        return self.status in {
            self.ST_IN_PROGRESS,
            self.ST_COMPLETED,
            self.ST_CANCELLED,
        }
    

    # job.models.job_orders.JobOrder

    from decimal import Decimal

    @property
    def discount_amount(self):
        if not self.discount_type or not self.discount_value:
            return Decimal("0")

        base = self.total_amount or Decimal("0")

        if self.discount_type == "AMOUNT":
            return min(self.discount_value, base)

        if self.discount_type == "PERCENT":
            pct = min(self.discount_value, Decimal("100"))
            return (base * pct / Decimal("100")).quantize(Decimal("0.01"))

        return Decimal("0")


    @property
    def down_payment_amount(self):
        percent = self.down_payment_percent or Decimal("0.00")
        base = self.grand_total or Decimal("0.00")

        if percent <= 0:
            return Decimal("0.00")

        return (base * percent) / Decimal("100")

    @property
    def remaining_balance(self):
        remaining = (self.grand_total or Decimal("0.00")) - self.down_payment_amount
        return remaining if remaining > 0 else Decimal("0.00")
    
    @property
    def subtotal_after_discount(self):
        total = self.total_amount or Decimal("0.00")
        discount = self.discount_amount or Decimal("0.00")
        return total - discount

    @property
    def total_invoiced(self):
        total = self.invoices.filter(
            invoice_type__in=["DP", "FINAL"]
        ).aggregate(
            total=Sum("total_amount")
        )["total"]
        return total or Decimal("0.00")
    
    @property
    def remaining_invoiceable(self):
        base = self.grand_total or Decimal("0.00")
        remaining = base - self.total_invoiced
        return remaining if remaining > 0 else Decimal("0.00")

    @property
    def has_dp(self):
        return bool(self.down_payment_percent and self.down_payment_percent > 0)

    @property
    def has_dp_invoice(self):
        return self.invoices.filter(invoice_type="DP").exists()

    @property
    def has_final_invoice(self):
        return self.invoices.filter(invoice_type="FINAL").exists()

    @property
    def can_generate_dp(self):
        return (
            self.status == self.ST_IN_COSTING
            and self.has_dp
            and not self.has_dp_invoice
        )

    @property
    def can_generate_final(self):
        return (
            self.status == self.ST_IN_PROGRESS
            and self.remaining_invoiceable > 0
            and (not self.has_dp or self.has_dp_invoice)
            and not self.has_final_invoice
        )


    # --- helpers transisi (opsional tapi saya rekomendasikan) ---
    

    # ===============================
    # CONFIRM (DRAFT → IN_COSTING)
    # ===============================
    def can_confirm(self):
        return self.status == self.ST_DRAFT


    def confirm(self, user):
        if not self.can_confirm():
            raise ValidationError("Job is not in DRAFT.")

        self.status = self.ST_IN_COSTING
        self.confirmed_at = timezone.now()
        self.confirmed_by = user

        # reset hold data
        self.hold_at = None
        self.hold_reason = ""


    # ===============================
    # START PROGRESS (IN_COSTING → IN_PROGRESS)
    # ===============================
    def can_start_progress(self):
        return self.status == self.ST_IN_COSTING


    def start_progress(self, user):
        if not self.can_start_progress():
            raise ValidationError("Job is not in IN_COSTING.")

        # 🔥 RULE BARU: jika ada DP, harus sudah dibuat
        if self.has_dp and not self.has_dp_invoice:
            raise ValidationError(
                "Down Payment invoice must be generated before moving to In Progress."
            )

        self.status = self.ST_IN_PROGRESS

        # reset hold data
        self.hold_at = None
        self.hold_reason = ""


    # ===============================
    # HOLD
    # ===============================
    def can_hold(self):
        return self.status == self.ST_IN_PROGRESS


    def hold(self, user, reason: str):
        if not self.can_hold():
            raise ValidationError("Job is not IN_PROGRESS.")

        if not (reason or "").strip():
            raise ValidationError("Hold reason is required.")

        self.status = self.ST_ON_HOLD
        self.hold_at = timezone.now()
        self.hold_reason = reason.strip()


    # ===============================
    # RESUME
    # ===============================
    def can_resume(self):
        return self.status == self.ST_ON_HOLD


    def resume(self, user):
        if not self.can_resume():
            raise ValidationError("Job is not ON_HOLD.")

        self.status = self.ST_IN_PROGRESS


    # ===============================
    # CANCEL
    # ===============================
    def can_cancel(self):
        return self.status in {
            self.ST_DRAFT,
            self.ST_IN_COSTING,
            self.ST_IN_PROGRESS,
            self.ST_ON_HOLD,
        }


    def cancel(self, user, reason: str):
        if not self.can_cancel():
            raise ValidationError("Job cannot be cancelled.")

        if not (reason or "").strip():
            raise ValidationError("Cancel reason is required.")

        self.status = self.ST_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancel_reason = reason.strip()


    # ===============================
    # COMPLETE (IN_PROGRESS → COMPLETED)
    # ===============================
    def complete(self, user):
        if self.status != self.ST_IN_PROGRESS:
            raise ValidationError("Job hanya bisa di-complete dari status In Progress.")

        if self.complete_journal_id:
            raise ValidationError("Job ini sudah pernah dibuat jurnal Complete.")

        costs = self.job_costs.filter(is_active=True)

        if not costs.exists():
            raise ValidationError("Tidak bisa Complete: belum ada job cost.")

        self.status = self.ST_COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save(update_fields=["status", "completed_at", "completed_by"])

        # auto posting COGS
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

        is_new = self.pk is None

        # ===== STATUS TRANSITION CHECK =====
        if not is_new:
            old = type(self).objects.get(pk=self.pk)

            # Jika status berubah
            if old.status != self.status:

                # Rule: tidak boleh masuk IN_PROGRESS jika DP belum dibuat
                if self.status == self.ST_IN_PROGRESS:
                    if self.has_dp and not self.has_dp_invoice:
                        raise ValidationError(
                            "Down Payment invoice must be generated before moving to In Progress."
                        )

        # ===== AUTO NUMBERING (existing logic) =====
        if is_new and not (self.number or "").strip():
            self.number = get_next_number("job", "JOB_ORDER")

        super().save(*args, **kwargs)

    @classmethod
    def visible(cls):
        # sesuai desain om: job status QUOTATION tidak muncul di list normal
        return cls.objects.exclude(status=cls.ST_QUOTATION)
    
    def clean(self):
        super().clean()

        # Rule: tidak boleh masuk IN_PROGRESS jika DP belum dibuat
        if self.status == self.ST_IN_PROGRESS:
            if self.has_dp and not self.has_dp_invoice:
                raise ValidationError(
                    "Down Payment invoice must be generated before moving to In Progress."
                )
        
    def convert_from_quotation(self, *, user=None, job_date=None):
        self.status = self.ST_DRAFT

        self.job_date = job_date or timezone.localdate()

        if user is not None and hasattr(self, "sales_user_id"):
            self.sales_user = user

        # selalu set nomor final saat convert
        self.number = get_next_number("job", "JOB_ORDER")

        update_fields = ["status", "job_date", "number"]
        if user is not None and hasattr(self, "sales_user_id"):
            update_fields.append("sales_user")

        self.save(update_fields=update_fields)


    @property
    def service_code(self) -> str:
        return (getattr(self.service, "code", "") or "").upper()

    @property
    def service_kind(self) -> str:
        if self.service_code.endswith("_SEA"):
            return "SEA"
        if self.service_code.endswith("_AIR"):
            return "AIR"
        return ""

    @property
    def service_display(self) -> str:
         name = getattr(self.service, "name", "") or "-"
         return f"{name} Services"


    @property
    def route_display(self) -> str:
        o = getattr(self.origin, "name", "") if self.origin else ""
        d = getattr(self.destination, "name", "") if self.destination else ""
        if o and d:
            return f"{o} - {d}"
        return o or d or "-"
    
    @property
    def d2d_display(self) -> str:
        lines = []
        if self.pickup:
            lines.append(f"Pick Up: {self.pickup}")
        if self.delivery:
            lines.append(f"Delivery: {self.delivery}")
        return "\n".join(lines)


    @property
    def is_d2d(self) -> bool:
        # sesuaikan logic deteksi D2D di project om:
        # opsi A: Service punya code
        code = (getattr(self.service, "code", "") or "").upper()
        if code:
            return code == "D2D"

        # opsi B fallback: cek nama service
        name = (getattr(self.service, "name", "") or "").upper()
        return "D2D" in name or "DOOR" in name

    @property
    def etd_display(self) -> str:
        if not self.shp_date:
            return "-"
        return formats.date_format(self.shp_date, "d-m-Y")


    @property
    def etd_display(self) -> str:
        if not self.shp_date:
            return "-"
        return formats.date_format(self.shp_date, "d-m-Y")

    @property
    def print_description(self) -> str:
        lines = []

        svc_name =   self.service_display

        # ===== P2P SEA / AIR =====
        if self.service_code in ("P2P_SEA", "P2P_AIR"):
            kind = self.service_kind
            header = f"{svc_name} ({kind})" if kind else svc_name
            lines.append(header)
            lines.append(self.route_display)

        # ===== D2D =====
        elif self.service_code == "D2D":
            lines.append(f"{svc_name} (D2D)")
            d2d = self.d2d_display
            if d2d:
                lines.append(d2d)

        # ===== fallback =====
        else:
            lines.append(svc_name)
            lines.append(self.route_display)

        # ===== ETD =====
        lines.append(f"ETD: {self.etd_display}")

        return "\n".join([l for l in lines if l and l.strip()])

    from decimal import Decimal


    @property
    def tax_rate_display(self) -> str:
        """
        Output contoh:
        - 1.1%
        - PPN 1.1%
        - PPN 1.1%, PPh 23 2%
        """
        items = self.taxes.all()
        if not items:
            return "-"

        parts = []
        for t in items:
            name = getattr(t, "name", "") or getattr(t, "code", "") or "Tax"

            # coba beberapa kemungkinan nama field rate
            rate = (
                getattr(t, "rate", None)
                or getattr(t, "percent", None)
                or getattr(t, "percentage", None)
                or getattr(t, "value", None)
            )

            if rate is None:
                parts.append(name)
                continue

            if isinstance(rate, Decimal):
                rate_str = str(rate.normalize())
            else:
                rate_str = str(rate).strip()

            parts.append(f"{name} {rate_str}%")

        return ", ".join(parts)

    @property
    def ppn_rate_display(self) -> str:
        ppn = self.taxes.filter(group="PPN").order_by("id").first()
        if not ppn:
            return "-"

        r = ppn.rate
        if isinstance(r, Decimal):
            r = r.normalize()
        return f"{r}%" 

    @property
    def ppn_label_rate_display(self) -> str:
        qs = self.taxes.filter(group="PPN").values_list("rate", flat=True)
        rates = list(qs)
        if not rates:
            return "-"

        out = []
        for r in rates:
            out.append(str(r.normalize() if hasattr(r, "normalize") else r))

        return f"PPN {' + '.join([x + '%' for x in out])}"


    
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

    
