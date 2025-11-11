# purchases/models.py
from django.db import models
from django.db.models import PROTECT, CASCADE
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

from core.utils import get_next_number
from core.models import Currency


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class PurchaseOrder(TimeStampedModel):
    # --- numbering & ref ---
    number = models.CharField(max_length=50, unique=True, null=True, blank=True, editable=False)
    ref_number = models.CharField(max_length=50, null=True, blank=True)

    # --- parties ---
    vendor = models.ForeignKey(
        "partners.PartnerRole",
        on_delete=PROTECT,
        related_name="purchase_orders",
        limit_choices_to={"role_type__code": "vendor"},  # ← ganti role → role_type
    )
    purchase_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        related_name="purchase_orders",
        db_index=True,
        null=True, blank=True,
        db_column="purchase_user_id",
    )

    # --- dates ---
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)

    # --- finance ---
    currency = models.ForeignKey(Currency, on_delete=PROTECT, related_name="purchase_orders")
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                      validators=[MinValueValidator(0), MaxValueValidator(100)])
    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # --- STATUS constants (selaras Sales Order) ---
    STATUS_DRAFT     = "DRAFT"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_PROGRESS  = "ON_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_HOLD      = "ON_HOLD"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PROGRESS, "On Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_HOLD, "On Hold"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # --- allowed transitions ---
    _ALLOWED_TRANSITIONS = {
        STATUS_DRAFT:     {STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_CONFIRMED: {STATUS_PROGRESS, STATUS_CANCELLED, STATUS_HOLD},
        STATUS_PROGRESS:  {STATUS_COMPLETED, STATUS_CANCELLED, STATUS_HOLD},
        STATUS_HOLD:      {STATUS_PROGRESS, STATUS_CANCELLED},
        STATUS_COMPLETED: set(),
        STATUS_CANCELLED: set(),
    }

    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to="purchases/po/%Y/%m/", null=True, blank=True)

    class Meta:
        db_table = "purchases_orders"
        indexes = [
            models.Index(fields=["number"]),
            models.Index(fields=["order_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vendor"]),   # <— perbaiki: vendor (bukan supplier)
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or "(un-numbered PO)"

    # numbering
    def ensure_number(self):
        if not self.number:
            self.number = get_next_number(app_label="purchases", code="PO", today=timezone.localdate())

    # totals
    def recompute_totals(self):
        subtotal = sum((l.line_subtotal() for l in self.lines.all()), 0)
        tax_amt = (subtotal - (self.discount_amount or 0)) * (self.tax_percent or 0) / 100
        total = subtotal - (self.discount_amount or 0) + tax_amt
        self.subtotal_amount = subtotal
        self.tax_amount = tax_amt
        self.total_amount = total

    # workflow helpers
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self._ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str, save: bool = True) -> bool:
        """Pindah status jika diizinkan; return True jika sukses."""
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])
        return True

    def save(self, *args, **kwargs):
        if not self.number:
            self.ensure_number()
        super().save(*args, **kwargs)


class PurchaseOrderLine(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=CASCADE, related_name="lines")
    line_no = models.PositiveIntegerField(default=1)

    product_name = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=300, blank=True)
    uom = models.ForeignKey("core.UOM", on_delete=PROTECT, null=True, blank=True)
    qty = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    line_discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "purchases_order_lines"
        ordering = ["purchase_order_id", "line_no"]                 # <— rapikan nama field
        unique_together = [("purchase_order", "line_no")]           # <— rapikan nama field

    def __str__(self):
        return f"{self.purchase_order.number or 'PO'} / {self.line_no}"

    def line_subtotal(self):
        return max((self.qty or 0) * (self.unit_price or 0) - (self.line_discount or 0), 0)
