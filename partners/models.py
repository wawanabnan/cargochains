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
    email = models.CharField(max_length=120, null=True, blank=True)
    phone = models.CharField(max_length=60, null=True, blank=True)
    mobile = models.CharField(max_length=30, null=True, blank=True)

    # NOTE: ini masih CharField sesuai model lama.
    # Nanti kalau mau, bisa diubah ke TextField/JSON untuk multi-url.
    websites = models.CharField(max_length=30, null=True, blank=True)

    company_name = models.CharField(
        max_length=100,
        verbose_name="Company Name",
        blank=True,
        null=True,
    )
    company_type = models.CharField(
        max_length=10,
        choices=COMPANY_TYPE_CHOICES,
        verbose_name="Company Type",
        blank=True,
        null=True,
    )

    is_individual = models.BooleanField(
        default=False,
        help_text="Centang jika perorangan; kosongkan jika perusahaan.",
    )
    is_pkp = models.BooleanField(
        default=False,
        help_text="Centang jika PKP (Pengusaha Kena Pajak).",
    )

    tax = models.CharField(
        "NPWP",
        max_length=50,
        null=True,
        blank=True,
        help_text="NPWP perusahaan / perorangan."
    )

    job_title = models.CharField(
        "Job Title",
        max_length=100,
        null=True,
        blank=True,
        help_text="Jabatan contact utama, misal: Direktur, Owner, Procurement."
    )

    # --- Alamat (legacy) ---
    # Tetap dipertahankan untuk data lama / display bebas / luar negeri.
    address = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    post_code = models.CharField(max_length=20, null=True, blank=True)

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
    address_line1 = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Jalan, nomor rumah, komplek, gedung.",
    )
    address_line2 = models.CharField(
        max_length=200,
        null=True,
        blank=True,
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
        limit_choices_to={"is_individual": False},  # hanya partner perusahaan
    )

    bank_name = models.CharField(max_length=120, blank=True, default="")
    bank_account = models.CharField(max_length=60, blank=True, default="")
    bank_account_name = models.CharField(max_length=120, blank=True, default="")
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

    # --- Roles (multi choice) ---
    # Ini cuma "shortcut" ManyToMany, pakai tabel existing partner_roles
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
        """
        Mengembalikan string daftar role:
        contoh: 'Customer, Vendor, Carrier'
        """
        qs = (
            PartnerRole.objects.filter(partner=self)
            .select_related("role_type")
            .values_list("role_type__name", flat=True)
        )
        names = sorted(set(qs))
        return ", ".join(names) if names else "-"

    @property
    def full_address_lines(self) -> list[str]:
        """
        Format (setiap bagian satu baris):
        - address_line1
        - address_line2
        - village + " - " + district
        - regency
        - province
        """
        lines = []

        # Alamat baris 1
        if self.address_line1:
            lines.append(self.address_line1)

        # Alamat baris 2 (opsional)
        if self.address_line2:
            lines.append(self.address_line2)

        # Village - District
        vd = []
        if self.village:
            vd.append(self.village.name)
        if self.district:
            vd.append(self.district.name)

        if vd:
            # gabungkan jadi "Kelurahan - Kecamatan"
            lines.append(" - ".join(vd))

        # Regency (Kota/Kabupaten)
        if self.regency:
            lines.append(self.regency.name)

        # Province
        if self.province:
            lines.append(self.province.name)

        return lines


    @property
    def full_address_text(self) -> str:
        """Multi-line address using newline."""
        return "\n".join(self.full_address_lines)


class CustomerManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(roles__code="customer")  # roles -> PartnerRoleTypes via M2M
            .distinct()
        )

class Customer(Partner):
    objects = CustomerManager()

    class Meta:
        proxy = True
        verbose_name = "Customer"
        verbose_name_plural = "Customers"


class PartnerRoleTypes(models.Model):
    code = models.CharField(max_length=50, unique=True, blank=True)
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
        return f"{self.partner.name} → {self.role}"

    @property
    def role(self):
        return self.role_type

    # ini sebenarnya lebih cocok di admin, tapi aku biarkan karena sudah ada
    def roles_display(self, obj):
        qs = (
            PartnerRole.objects.filter(partner=obj)
            .select_related("role_type")
            .values_list("role_type__name", flat=True)
        )
        names = sorted(set(qs))
        return ", ".join(names) if names else "-"
