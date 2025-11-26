# sales/freight.py
from django.db.models import PROTECT
from django.db import models
from django.conf import settings

from core.models import TimeStampedModel, SalesService, Currency
from partners.models import Partner
from geo.models import Location
from django.db import transaction
from core.models import NumberSequence
from core.utils import get_next_number
from core.models import PaymentTerm,UOM


# ============================
#   FREIGHT QUOTATION STATUS
# ============================
class FreightQuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent to customer"
    ACCEPTED = "ACCEPTED", "Accepted"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"
    ORDERED = "ORDERED", "Converted to Order"


# ============================
#   FREIGHT QUOTATION
# ============================
class FreightQuotation(TimeStampedModel):
    """
    1 quotation = 1 origin + 1 destination
    Menyimpan snapshot shipper & consignee (nama, telp, alamat, geo).
    """

    # --- BASIC INFO ---
    number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )
    quotation_date = models.DateField()
    valid_until = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=FreightQuotationStatus.choices,
        default=FreightQuotationStatus.DRAFT,
        db_index=True,
    )

    # --- CUSTOMER ---
    customer = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="freight_quotations_as_customer",
    )
    customer_contact = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="freight_quotations_customer_contact",
    )

    # --- ROUTE & SERVICE ---
    origin = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="freight_quotations_origin",
    )
    destination = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="freight_quotations_destination",
    )
    sales_service = models.ForeignKey(
        SalesService,
        on_delete=models.PROTECT,
        related_name="freight_quotations_service",
        null=True,
        blank=True,

    )
    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_agency_quotations"
    )



    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, 
        related_name="freight_quotations_payment_terms", 
        null=True, blank=True
    )

    # --- PRICE ---
    currency = models.ForeignKey(
        Currency,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
        )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount  = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    # --- CARGO ---
    cargo_name = models.CharField(max_length=200, blank=True)
    hs_code = models.CharField(max_length=30, blank=True)
    commodity = models.CharField(max_length=200, blank=True)

    package_count = models.PositiveIntegerField(null=True, blank=True)
    package_type = models.CharField(max_length=50, blank=True)

    gross_weight = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
   
    volume_cbm = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    weight_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fo_weight",
        limit_choices_to={"category__iexact": "weight"},
    )

    volume_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fq_volume",
        limit_choices_to={"category__iexact": "volume"},
    )

    package_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fq_package",
        limit_choices_to={"category__iexact": "count"},
    )


    is_dangerous_goods = models.BooleanField(default=False)
    dangerous_goods_class = models.CharField(max_length=50, blank=True)
    shipment_plan_date = models.DateField(null=True, blank=True)

    # --- SHIPPER SNAPSHOT (COCOK DB: shipper_contact_name) ---
    shipper = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="freight_quotations_as_shipper",
    )
    shipper_contact_name = models.CharField(max_length=200, blank=True)
    shipper_phone = models.CharField(max_length=50, blank=True)
    shipper_address = models.TextField(blank=True)

    shipper_province = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_shipper_province",
    )
    shipper_regency = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_shipper_regency",
    )
    shipper_district = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_shipper_district",
    )
    shipper_village = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_shipper_village",
    )

    # --- CONSIGNEE SNAPSHOT (COCOK DB: consignee_name + consignee_address) ---
    consignee = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="freight_quotations_as_consignee",
    )
    consignee_name = models.CharField(max_length=255, blank=True)
    consignee_phone = models.CharField(max_length=50, blank=True)
    consignee_address = models.TextField(blank=True)

    # NB: di DB sekarang belum ada kolom geo consignee.
    # Kalau om mau, kita bisa tambahkan via migrasi baru (consignee_province_id, dst).
    consignee_province = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_consignee_province",
    )
    consignee_regency = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_consignee_regency",
    )
    consignee_district = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_consignee_district",
    )
    consignee_village = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fq_consignee_village",
    )

    # --- ADMIN / SALES ---
    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="freight_quotations",
    )

    notes_internal = models.TextField(blank=True)
    notes_customer = models.TextField(blank=True)

    class Meta:
        db_table = "sales_freight_quotations"
        ordering = ["-quotation_date", "-id"]

    def __str__(self):
        return f"{self.number} - {self.customer}"

    # -------- STATUS TRANSITION HELPER --------
    def can_transition_to(self, new_status: str) -> bool:
        """
        Enforce allowed transitions:
        DRAFT -> SENT
        SENT -> {ACCEPTED, CANCELLED, EXPIRED}
        ACCEPTED -> {CANCELLED, ORDERED}
        ORDERED, CANCELLED, EXPIRED -> final
        """
        current = self.status

        if current == FreightQuotationStatus.DRAFT:
            return new_status in {FreightQuotationStatus.SENT}

        if current == FreightQuotationStatus.SENT:
            return new_status in {
                FreightQuotationStatus.ACCEPTED,
                FreightQuotationStatus.CANCELLED,
                FreightQuotationStatus.EXPIRED,
            }

        if current == FreightQuotationStatus.ACCEPTED:
            return new_status in {
                FreightQuotationStatus.CANCELLED,
                FreightQuotationStatus.ORDERED,
            }

        # final states
        if current in {
            FreightQuotationStatus.CANCELLED,
            FreightQuotationStatus.EXPIRED,
            FreightQuotationStatus.ORDERED,
        }:
            return False

        return False

    def set_status(self, new_status: str, save=True) -> bool:
        """
        Helper:
        if fq.set_status(FreightQuotationStatus.SENT):
            ...
        """
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        if save:
            self.save(update_fields=["status"])
        return True

    def save(self, *args, **kwargs):
        if not self.number:
            if not self.number:
            # app_label dan code bebas, tapi konsisten dengan NumberSequence
                self.number = get_next_number("sales", "FREIGHT_QUOTATION")
        super().save(*args, **kwargs)

    @property
    def route_name(self):
        """
        Return origin - destination (name only, without kind).
        """
        if self.origin and self.destination:
            return f"{self.origin.name} - {self.destination.name}"
        if self.origin:
            return self.origin.name
        if self.destination:
            return self.destination.name
        return ""
    
    @property
    def display_name(self):
        return self.name


# ============================
#   FREIGHT ORDER STATUS
# ============================
class FreightOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


# ============================
#   FREIGHT ORDER
# ============================
class FreightOrder(TimeStampedModel):
    number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )
    order_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=FreightOrderStatus.choices,
        default=FreightOrderStatus.DRAFT,
        db_index=True,
    )

    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=PROTECT, 
        related_name="freight_orders_payment_terms",  
        null=True, blank=True
    )
    quotation = models.OneToOneField(
        FreightQuotation,
        on_delete=models.PROTECT,
        related_name="freight_order",
        null=True,
        blank=True,
    )

    customer = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="freight_orders",
    )

    origin = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="freight_orders_origin_set",
    )
    destination = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="freight_orders_destination_set",
    )

    sales_service = models.ForeignKey(
        SalesService,
        on_delete=models.PROTECT,
        related_name="freight_orders",
        null=True,
        blank=True,
    )

    sales_agency = models.ForeignKey(
        Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_agency_order"
    )


    # snapshot shipper & consignee name/address
    shipper_name = models.CharField(max_length=255, blank=True)
    shipper_address = models.TextField(blank=True)
    consignee_name = models.CharField(max_length=255, blank=True)
    consignee_address = models.TextField(blank=True)

    cargo_name = models.CharField(max_length=200, blank=True)
    package_count = models.PositiveIntegerField(null=True, blank=True)
    package_type = models.CharField(max_length=50, blank=True)
    gross_weight = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    volume_cbm = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    volume_cbm = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    weight_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fq_weight",
        limit_choices_to={"category__iexact": "weight"},
    )

    volume_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fo_volume",
        limit_choices_to={"category__iexact": "volume"},
    )

    package_uom = models.ForeignKey(
        UOM,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="fo_package",
        limit_choices_to={"category__iexact": "count"},
    )


    is_dangerous_goods = models.BooleanField(default=False)
    dangerous_goods_class = models.CharField(max_length=50, blank=True)
    shipment_plan_date = models.DateField(null=True, blank=True)


    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="freight_orders",
        null=True,
        blank=True,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
        )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount  = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )


    notes_internal = models.TextField(blank=True)

    class Meta:
        db_table = "sales_freight_orders"
        ordering = ["-order_date", "-id"]

    def __str__(self):
        return self.number
