from django.conf import settings
from django.db import models
from geo.models import Location
from decimal import Decimal


class Partner(models.Model):
    COMPANY_TYPE_CHOICES = [
        ("PT", "PT"),
        ("CV", "CV"),
        ("UD", "UD"),
        ("UKM", "UKM"),
    ]

    # --- Data umum ---
    name = models.CharField(max_length=120)

    # ✅ optional string: jangan null, biar konsisten & aman insert
    email = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=60, blank=True, default="")
    mobile = models.CharField(max_length=30, blank=True, default="")

    # ✅ max_length 30 terlalu pendek untuk URL; default empty string
    websites = models.CharField(max_length=255, blank=True, default="")

    company_name = models.CharField(
        max_length=100,
        verbose_name="Company Name",
        blank=True,
        default="",
    )
    company_type = models.CharField(
        max_length=10,
        choices=COMPANY_TYPE_CHOICES,
        verbose_name="Company Type",
        blank=True,
        default="",
    )

    # ✅ boolean sudah aman (non-null by design)
    is_individual = models.BooleanField(
        default=False,
        help_text="Centang jika perorangan; kosongkan jika perusahaan.",
    )
    is_pkp = models.BooleanField(
        default=False,
        help_text="Centang jika PKP (Pengusaha Kena Pajak).",
    )

    # ✅ optional string: jangan null
    tax = models.CharField(
        "NPWP",
        max_length=50,
        blank=True,
        default="",
        help_text="NPWP perusahaan / perorangan."
    )

    job_title = models.CharField(
        "Job Title",
        max_length=100,
        blank=True,
        default="",
        help_text="Jabatan contact utama, misal: Direktur, Owner, Procurement."
    )

    # --- Alamat (legacy) ---
    # ✅ optional text/string: jangan null
    address = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    post_code = models.CharField(max_length=20, blank=True, default="")

    # --- Alamat terstruktur (baru, untuk Indonesia & pakai geo.Location) ---
    location = models.ForeignKey(
        "geo.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="location_id",
        related_name="partners",
        help_text="Pilih lokasi administrasi (kelurahan/kecamatan/kota) jika diketahui.",
    )

    # ✅ optional string: jangan null
    address_line1 = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Jalan, nomor rumah, komplek, gedung.",
    )
    address_line2 = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="RT/RW, blok, lantai, atau info tambahan lain.",
    )

    province = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners_province",
        limit_choices_to={"kind": "province"},
        db_index=True,
        db_column="province_id"
    )
    regency = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners_regency",
        limit_choices_to={"kind": "regency"},
        db_index=True,
        db_column="regency_id"
    )
    district = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners_district",
        limit_choices_to={"kind": "district"},
        db_index=True,
        db_column="district_id"
    )
    village = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partners_village",
        limit_choices_to={"kind": "village"},
        db_index=True,
        db_column="village_id"
    )

    company = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="contacts",
        limit_choices_to={"is_individual": False},
    )

    bank_name = models.CharField(max_length=120, blank=True, default="")
    bank_account = models.CharField(max_length=60, blank=True, default="")
    bank_account_name = models.CharField(max_length=120, blank=True, default="")

    # ✅ decimal default sudah aman
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    is_sales_contact = models.BooleanField(
        default=False,
        help_text="Centang jika contact ini dipakai untuk Quotation / Sales Order.",
    )
    is_billing_contact = models.BooleanField(
        default=False,
        help_text="Centang jika contact ini dipakai untuk Invoice / Billing.",
    )

    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partners",
        db_index=True,
        null=True,
        blank=True,
        db_column="sales_user_id",
        help_text="PIC sales/AM yang bertanggung jawab.",
    )

    roles = models.ManyToManyField(
        "PartnerRoleTypes",
        through="PartnerRole",
        related_name="partners",
        blank=True,
        help_text="Peran partner (Customer, Vendor, Carrier, Agent, dll).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partners"
        indexes = [
            models.Index(fields=["name"], name="partners_name_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def roles_display(self):
        qs = (
            PartnerRole.objects.filter(partner=self)
            .select_related("role_type")
            .values_list("role_type__name", flat=True)
        )
        names = sorted(set(qs))
        return ", ".join(names) if names else "-"

    @property
    def full_address_lines(self) -> list[str]:
        lines = []

        if self.address_line1:
            lines.append(self.address_line1)

        if self.address_line2:
            lines.append(self.address_line2)

        vd = []
        if self.village:
            vd.append(self.village.name)
        if self.district:
            vd.append(self.district.name)

        if vd:
            lines.append(" - ".join(vd))

        if self.regency:
            lines.append(self.regency.name)

        if self.province:
            lines.append(self.province.name)

        return lines

    @property
    def full_address_text(self) -> str:
        return "\n".join(self.full_address_lines)

    @property
    def address_lines(self):
        def pick(*names):
            """Ambil nilai pertama yang ada & tidak kosong dari beberapa nama field."""
            for n in names:
                if hasattr(self, n):
                    v = getattr(self, n)
                    if v is None:
                        continue
                    v = str(v).strip()
                    if v:
                        return v
            return ""

        def nm(x):
            """Kalau FK object ambil .name, kalau string ya string."""
            if not x:
                return ""
            return (getattr(x, "name", None) or str(x)).strip()
        
        def norm(s: str) -> str:
            return " ".join((s or "").split()).lower()


        lines = []
        seen = set()
        
        # 1) address lines (support dua kemungkinan nama field)
        a1 = pick("address_line1", "address_line_1")
        a2 = pick("address_line2", "address_line_2")

        if a1:
            lines.append(a1)
        if a2 and a2 != a1:          # ✅ anti dobel
            lines.append(a2)

        
        def add(line: str):
            line = (line or "").strip()
            if not line:
                return
            key = norm(line)
            if key in seen:
                return
            seen.add(key)
            lines.append(line)

        village = nm(getattr(self, "village", None))
        district = nm(getattr(self, "district", None))
        vd = " - ".join([x for x in [village, district] if x])
        add(vd)

        # 3) regency
        add(nm(getattr(self, "regency", None)))

        # 4) province
        add(nm(getattr(self, "province", None)))

        return lines
    

class CustomerManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(roles__code__iexact="customer")  # aman upper/lower
            .distinct()
        )


class Customer(Partner):
    objects = CustomerManager()

    class Meta:
        proxy = True
        verbose_name = "Customer"
        verbose_name_plural = "Customers"


class VendorManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(roles__code__in=["vendor", "carrier"])  # sesuaikan kode role
            .distinct()
        )


class Vendor(Partner):
    objects = VendorManager()

    class Meta:
        proxy = True
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"


class PartnerRoleTypes(models.Model):
    # ✅ UNIQUE + blank=True itu rawan ("" duplikat). Lebih aman: jangan blank.
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_role_types"
        verbose_name = "Partner Role Types"
        verbose_name_plural = "Partner Roles Type"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PartnerRole(models.Model):
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="partner_roles",
    )
    role_type = models.ForeignKey(
        PartnerRoleTypes,
        on_delete=models.CASCADE,
        related_name="partner_roles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_roles"
        unique_together = ("partner", "role_type")
        verbose_name = "Partner Role"
        verbose_name_plural = "Partner Roles"

    def __str__(self):
        return f"{self.partner.name} → {self.role_type.name}"




from partners.models import Partner, PartnerRoleTypes, PartnerRole

names = [
    "Pelayaran Sumber Karya Samudera",
    "SAII RESOURCES Pte ltd",
    "Abdi Karya Indo 99",
    "Orecon Putra Perkasa",
    "Anda Auto Indonesia",
    "Tracon",
    "Indocahaya Wira Nusantara",
    "Rajawali Emas Ancora Lestari",
    "Ezmar Transmitra Cargo",
]

# ambil role CUSTOMER
