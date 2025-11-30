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
from datetime import date

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

    # === NEW: reference info ===
    REFERENCE_TYPES = [
        ("CUSTOMER_PO", "Customer PO"),
        ("EMAIL", "Email"),
        ("QUOTATION", "Quotation"),
    ]

    reference_type = models.CharField(
        max_length=30,
        choices=REFERENCE_TYPES,
        null=True,
        blank=True,
    )
    reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

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
    

    @property
    def customer_address_lines(self):
        return self.customer.full_address_lines if self.customer_id else []

    @property
    def customer_address_text(self):
        return self.customer.full_address_text if self.customer_id else ""


    # =========================
    #  ADDRESS HELPERS
    # =========================
    @property
    def shipper_address_lines(self):
        """
        Format:
        - Contact name
        - Company (kalau ada)
        - Phone number
        - Address
        - Village - District
        - Regency
        - Province
        """
        lines = []

        # 1) Contact / person
        if self.shipper_contact_name:
            lines.append(self.shipper_contact_name)

        # 2) Company (dari Partner)
        company = None
        if self.shipper:
            company = self.shipper.company_name or self.shipper.name
        if company:
            lines.append(company)

        # 3) Phone
        phone = self.shipper_phone
        if not phone and self.shipper:
            phone = self.shipper.phone or self.shipper.mobile
        if phone:
            lines.append(phone)

        # 4) Address (free text)
        if self.shipper_address:
            lines.append(self.shipper_address)

        # 5) Village - District
        village_name = getattr(self.shipper_village, "name", None)
        district_name = getattr(self.shipper_district, "name", None)
        if village_name or district_name:
            parts = [p for p in [village_name, district_name] if p]
            lines.append(" - ".join(parts))

        # 6) Regency
        regency_name = getattr(self.shipper_regency, "name", None)
        if regency_name:
            lines.append(regency_name)

        # 7) Province
        province_name = getattr(self.shipper_province, "name", None)
        if province_name:
            lines.append(province_name)

        return lines

    @property
    def consignee_address_lines(self):
        """
        Format:
        - Contact name
        - Company (kalau ada)
        - Phone number
        - Address
        - Village - District
        - Regency
        - Province
        """
        lines = []

        # 1) Contact / person
        if self.consignee_name:
            lines.append(self.consignee_name)

        # 2) Company (dari Partner)
        company = None
        if self.consignee:
            company = self.consignee.company_name or self.consignee.name
        if company:
            lines.append(company)

        # 3) Phone
        phone = self.consignee_phone
        if not phone and self.consignee:
            phone = self.consignee.phone or self.consignee.mobile
        if phone:
            lines.append(phone)

        # 4) Address (free text)
        if self.consignee_address:
            lines.append(self.consignee_address)

        # 5) Village - District
        village_name = getattr(self.consignee_village, "name", None)
        district_name = getattr(self.consignee_district, "name", None)
        if village_name or district_name:
            parts = [p for p in [village_name, district_name] if p]
            lines.append(" - ".join(parts))

        # 6) Regency
        regency_name = getattr(self.consignee_regency, "name", None)
        if regency_name:
            lines.append(regency_name)

        # 7) Province
        province_name = getattr(self.consignee_province, "name", None)
        if province_name:
            lines.append(province_name)

        return lines

    def generate_order(self, user=None):
        """
        Generate Freight Order (Sales Order) dari quotation ini.

        - Membuat FreightOrder dengan status DRAFT
        - Menyalin data utama dari quotation
        - Link balik ke self.freight_order (kalau fieldnya ada)
        - Tidak mengubah status quotation (status diatur di view)
        """

        # Kalau sudah pernah generate → jangan bikin dua kali
        if getattr(self, "freight_order_id", None):
            return self.freight_order

        # Di file yang sama biasanya sudah ada:
        # class FreightOrder(models.Model): ...
        # class FreightOrderStatus(models.TextChoices): ...
        # Jadi kita bisa pakai langsung nama kelasnya.
        with transaction.atomic():
            order = FreightOrder.objects.create(
                # --- STATUS ORDER SELALU DRAFT ---
                status=FreightOrderStatus.DRAFT,

                # --- RELASI KE QUOTATION (jika fieldnya ada di FreightOrder) ---
                # Sesuaikan dengan nama field di model FreightOrder om
                # misalnya: freight_quotation atau quotation
                **(
                    {"freight_quotation": self}
                    if "freight_quotation" in [f.name for f in FreightOrder._meta.fields]
                    else {}
                ),

                # --- SALES / CUSTOMER ---
                customer=self.customer,
                sales_user=user or self.sales_user,
                sales_service=self.sales_service,
                payment_term=self.payment_term,
                currency=self.currency,

                # --- ROUTE ---
                origin=self.origin,
                destination=self.destination,
                shipment_plan_date=self.shipment_plan_date,

                # --- CARGO INFO ---
                cargo_name=self.cargo_name,
                hs_code=self.hs_code,
                package_count=self.package_count,
                gross_weight=self.gross_weight,
                volume_cbm=self.volume_cbm,
                # Kalau FreightOrder tidak punya field-field ini,
                # tinggal hapus barisnya.
                volume_uom=getattr(self, "volume_uom", None),
                weight_uom=getattr(self, "weight_uom", None),
                package_uom=getattr(self, "package_uom", None),

                # --- SHIPPER ---
                shipper=self.shipper,
                shipper_contact_name=self.shipper_contact_name,
                shipper_phone=self.shipper_phone,
                shipper_address=self.shipper_address,
                shipper_province=self.shipper_province,
                shipper_regency=self.shipper_regency,
                shipper_district=self.shipper_district,
                shipper_village=self.shipper_village,

                # --- CONSIGNEE ---
                consignee=self.consignee,
                consignee_name=self.consignee_name,
                consignee_phone=self.consignee_phone,
                consignee_address=self.consignee_address,
                consignee_province=self.consignee_province,
                consignee_regency=self.consignee_regency,
                consignee_district=self.consignee_district,
                consignee_village=self.consignee_village,

                # --- PRICING & TAX ---
                quantity=self.quantity,
                unit_price=self.unit_price,
                amount=self.amount,
                discount_percent=getattr(self, "discount_percent", None),
                discount_amount=getattr(self, "discount_amount", None),
                tax_percent=self.tax_percent,
                tax_amount=self.tax_amount,
                total_amount=self.total_amount,

                # --- NOTES (kalau field ada di FreightOrder) ---
                notes_customer=getattr(self, "notes_customer", None),
                notes_internal=getattr(self, "notes_internal", None),
            )

            # Link balik ke quotation kalau ada field-nya
            if hasattr(self, "freight_order"):
                self.freight_order = order
                self.save(update_fields=["freight_order"])

        return order


# ============================
#   FREIGHT ORDER STATUS
# ============================
class FreightOrderStatus(models.TextChoices):
    DRAFT        = "DRAFT", "Draft"
    IN_PROGRESS  = "IN_PROGRESS", "In Progress"
    COMPLETED    = "COMPLETED", "Completed"
    CANCELLED    = "CANCELLED", "Cancelled"
    HOLDED       = "HOLDED", "Holded"

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
    ref_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        db_index=True,
    )
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
    down_payment = models.DecimalField(
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
    notes_customer = models.TextField(blank=True)

    # === NEW: reference info ===
    REFERENCE_TYPES = [
        ("CUSTOMER_PO", "Customer PO"),
        ("EMAIL", "Email"),
        ("QUOTATION", "Quotation"),
    ]

    reference_type = models.CharField(
        max_length=30,
        choices=REFERENCE_TYPES,
        null=True,
        blank=True,
    )
    reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    reference_date = models.DateField(default=date.today)
    
    class Meta:
        db_table = "sales_freight_orders"
        ordering = ["-order_date", "-id"]

    def __str__(self):
        return self.number
