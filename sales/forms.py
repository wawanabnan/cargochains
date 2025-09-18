from django import forms
from django.forms import BaseInlineFormSet
from datetime import date as _date, timedelta
from .models import SalesQuotation, SalesQuotationLine, Partner
# kalau PartnerRole ada di app "partners"
try:
    from partners.models import PartnerRole
except Exception:
    PartnerRole = None


class SalesServiceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return getattr(obj, "name", str(obj))


class QuotationHeaderForm(forms.ModelForm):
    class Meta:
        model = SalesQuotation
        fields = [
            "customer",
            "sales_service",
            "sales_agency",   # hanya partner yg punya roles.role='agency'
            "currency",
            "payment_term",
            "valid_until",
            "note_1",
            "date",           # hidden + auto today
        ]
        widgets = {
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "note_1": forms.Textarea(attrs={"rows": 3}),
            "date": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Label sales_service tanpa code
        if "sales_service" in self.fields:
            base = self.fields["sales_service"]
            self.fields["sales_service"] = SalesServiceChoiceField(
                queryset=base.queryset,
                required=base.required,
                empty_label=getattr(base, "empty_label", "---------"),
                label=base.label or "Sales service",
                help_text=base.help_text,
                widget=base.widget,
            )

        # sales_agency: Partner yg punya roles.role='agency'
        if "sales_agency" in self.fields:
            if PartnerRole is not None:
                partner_ids = PartnerRole.objects.filter(role__iexact="agency") \
                                                 .values_list("partner_id", flat=True)
                self.fields["sales_agency"].queryset = Partner.objects.filter(id__in=partner_ids).distinct()
            else:
                # fallback ke reverse relation 'roles'
                self.fields["sales_agency"].queryset = Partner.objects.filter(
                    roles__role__iexact="agency"
                ).distinct()

        # default tanggal
        if not self.data.get("valid_until") and not self.initial.get("valid_until"):
            self.fields["valid_until"].initial = _date.today() + timedelta(days=7)
        if "date" in self.fields and not (self.data.get("date") or self.initial.get("date")):
            self.fields["date"].initial = _date.today()

        # currency default IDR
        if "currency" in self.fields and not (self.data.get("currency") or self.initial.get("currency")):
            try:
                CurrencyModel = self.fields["currency"].queryset.model
                idr = CurrencyModel.objects.get(code="IDR")
                self.fields["currency"].initial = idr.pk
            except Exception:
                pass

    def clean_date(self):
        return self.cleaned_data.get("date") or _date.today()


class QuotationLineForm(forms.ModelForm):
    class Meta:
        model = SalesQuotationLine
        # origin & destination FK ke geo.Location (sudah ada di model)
        fields = ["origin", "destination", "description", "qty", "uom", "price"]

    def clean_qty(self):
        v = self.cleaned_data.get("qty")
        if v is not None and v <= 0:
            raise forms.ValidationError("Qty harus > 0.")
        return v

    def clean_price(self):
        v = self.cleaned_data.get("price")
        if v is not None and v < 0:
            raise forms.ValidationError("Price tidak boleh negatif.")
        return v


class BaseLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_forms = [f for f in self.forms if not (getattr(f, "cleaned_data", {}) or {}).get("DELETE")]
        # minimal 1 baris valid
        any_has_data = False
        for f in active_forms:
            cd = getattr(f, "cleaned_data", {})
            # kalau semua field kosong, lewati
            if not cd:
                continue
            # dianggap ada data jika salah satu kolom penting terisi
            if any(cd.get(k) for k in ("origin", "destination", "description", "qty", "uom", "price")):
                any_has_data = True
        if not any_has_data:
            raise forms.ValidationError("Minimal satu line harus diisi.")
