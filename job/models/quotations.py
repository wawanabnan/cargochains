from django.db import models, transaction
from django.db.models import PROTECT
from django.core.exceptions import ValidationError
from django.utils import timezone
from job.models.job_orders import JobOrder
from core.utils.numbering import get_next_number
from core.models.settings import CoreSetting
from datetime import timedelta
from core.services.core_settings import calc_valid_until


class QuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    EXPIRED = "EXPIRED", "Expired"
    ORDERED = "ORDERED", "Ordered"
    CANCELED = "CANCELED", "Canceled"


class Quotation(models.Model):
    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
        db_index=True,
    )

    job_order = models.OneToOneField(
        JobOrder,
        on_delete=PROTECT,   # aman: kita delete quotation dulu baru delete job_order
        null=True,
        blank=True,
        related_name="quotation",
    )

    number = models.CharField("Quotation No", max_length=30, unique=True, db_index=True)
    quote_date = models.DateField("Quote Date", default=timezone.localdate)
    valid_until = models.DateField("Valid Until", null=True, blank=True, db_index=True)

    # timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_quotations"
    )
    
    expired_at = models.DateTimeField(null=True, blank=True)
    expired_by_system = models.BooleanField(default=False)  # optional


    ordered_at = models.DateTimeField(blank=True, null=True)
    ordered_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="ordered_quotations"
    )

    canceled_at = models.DateTimeField(null=True, blank=True)
    canceled_by = models.ForeignKey(
         "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="cancel_quotations"

    )
    cancel_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # actor (di-set dari view saat update status)
    _sales_user = None

    class Meta:
        db_table = "quotations"
        ordering = ["-quote_date", "-id"]
        indexes = [models.Index(fields=["status", "valid_until"])]
        permissions = [
            ("can_send_quotation", "Can send quotation"),
            ("can_convert_quotation", "Can convert quotation to order"),
        ]


    def __str__(self):
        return self.number

    def clean(self):
        if self.valid_until and self.quote_date and self.valid_until < self.quote_date:
            raise ValidationError({"valid_until": "Valid Until tidak boleh lebih kecil dari Quote Date."})

    

    def delete(self, *args, **kwargs):
        """
        Kalau quotation EXPIRED dihapus, job_order ikut terhapus.
        """
        job_id = self.job_order_id
        st = self.status

        with transaction.atomic():
            super().delete(*args, **kwargs)
            if st == QuotationStatus.EXPIRED and job_id:
                JobOrder.objects.filter(pk=job_id).delete()

    # helper optional
    def mark_expired(self):
        if self.status == QuotationStatus.EXPIRED:
            return
        self.status = QuotationStatus.EXPIRED
        self.expired_at = self.expired_at or timezone.now()

    @property
    def is_expired(self):
        return bool(self.valid_until and timezone.localdate() > self.valid_until)

    def extend_validity(self, new_valid_until, user=None):
        self.valid_until = new_valid_until
        if self.status == QuotationStatus.EXPIRED:
            # balikkan ke SENT atau DRAFT sesuai kebijakanmu
            self.status = QuotationStatus.SENT
            self.expired_at = None
            self.expired_by_system = False
        self.save()

    def mark_sent(self, user):
        if self.is_expired:
            raise ValidationError("Quotation sudah EXPIRED. Extend valid_until dulu.")
        if self.status != QuotationStatus.DRAFT:
            raise ValidationError("Hanya quotation DRAFT yang bisa di-set menjadi SENT.")
        self.status = QuotationStatus.SENT
        self.sent_at = timezone.now()
        self.sent_by = user
        self.save(update_fields=["status", "sent_at", "sent_by"])


    def mark_ordered(self, user):
        if self.status not in [QuotationStatus.SENT, QuotationStatus.DRAFT]:
            raise ValidationError("Quotation harus minimal SENT untuk di-convert menjadi ORDERED.")
        self.status = QuotationStatus.ORDERED
        self.ordered_at = timezone.now()
        self.ordered_by = user
        self.save(update_fields=["status", "ordered_at", "ordered_by"])


    def get_quotation_valid_days(default=7) -> int:
        s = CoreSetting.objects.filter(code__iexact="QUOTATION_VALID_DAY").first()
        return int(s.int_value) if s and s.int_value is not None else default


    def save(self, *args, **kwargs):
        if not self.pk and not (self.number or "").strip():
            self.number = get_next_number("job", "QUOTATION")
            tmp = get_next_number("job", "QUOTATION")
            print("DEBUG QUOTATION NUMBER:", tmp)
            self.number = tmp

        if not self.valid_until and self.quote_date:
            self.valid_until = calc_valid_until(base_date=self.quote_date)  # sales + QUOTATION_VALID_DAY default
    
        super().save(*args, **kwargs)