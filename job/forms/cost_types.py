from django import forms

from job.models.costs import JobCostType
from accounting.models.chart import Account
from accounting.models.settings import AccountingSettings

  
SYSTEM_GROUP_CHOICES = [
    ("TRUCKING", "Trucking"),
    ("WAREHOUSE", "Warehouse"),
    ("OCEAN", "Ocean Freight"),
    ("AIR", "Air Freight"),
    ("PORT", "Port / Stevedoring"),
    ("DOC", "Documentation"),
    ("OTHER", "Other / Internal"),
]
   

class JobCostTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # terima request (opsional)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # ✅ UX: ganti label agar sesuai bahasa Job Order
        self.fields["code"].label = "Code"
        self.fields["name"].label = "Cost / Service Name"
        self.fields["requires_vendor"].label = "Vendor required"
        self.fields["is_active"].label = "Active"

        # ✅ cost_group jadi dropdown kategori sistem (bukan text bebas)
        self.fields["cost_group"].label = "Category (system)"
        self.fields["cost_group"].help_text = (
            "Hanya untuk aturan sistem (tidak ditampilkan di Job Order). "
            "Pilih kategori yang paling cocok."
        )
        self.fields["cost_group"].widget = forms.Select(
            attrs={"class": "form-select form-select-sm"}
        )

        # merge: pilihan default + value lama yang sudah ada di DB (biar tidak putus)
        existing = (
            JobCostType.objects.exclude(cost_group__isnull=True)
            .exclude(cost_group="")
            .values_list("cost_group", flat=True)
            .distinct()
        )
        extra = [(g, g) for g in existing if g not in dict(SYSTEM_GROUP_CHOICES)]
        self.fields["cost_group"].choices = SYSTEM_GROUP_CHOICES + extra

        # ✅ Filter COGS account (kalau settings ada)
        year = None
        try:
            year = AccountingSettings.objects.get().active_year
        except Exception:
            year = None

        qs = Account.objects.all()
        try:
            qs = qs.filter(type="expense")
        except Exception:
            pass

        if year:
            try:
                qs = qs.filter(chart_year=year)
            except Exception:
                pass

        # kalau om memang pakai kode 51xxx = COGS, aktifkan filter ini
        try:
            qs = qs.filter(code__startswith="51")
        except Exception:
            pass

        self.fields["cogs_account"].queryset = qs.order_by("code")

    class Meta:
        model = JobCostType
        fields = [
            "code",
            "name",
            "requires_vendor",
            "is_active",
            "cost_group",
            "cogs_account",
            "sort_order",
            "service_type",
            "accrued_liability_account"
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "service_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "accrued_liability_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "requires_vendor": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "cogs_account": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        }
