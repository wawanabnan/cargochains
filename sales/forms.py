from django import forms
from django.forms import BaseInlineFormSet
from datetime import date as _date, timedelta
from .models import SalesQuotation, SalesQuotationLine, Partner
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
            "customer",       # hanya partners role='customer'
            "sales_service",
            "sales_agency",   # hanya partners role='agency'
            "currency",
            "payment_term",
            "valid_until",
            "note_1",
            "date",           # hidden + auto today
        ]
        widgets = {
             "customer":      forms.Select(attrs={"class": "form-select"}),
            "sales_service": forms.Select(attrs={"class": "form-select"}),
            "sales_agency":  forms.Select(attrs={"class": "form-select"}),
            "currency":      forms.Select(attrs={"class": "form-select"}),
            "payment_term":  forms.Select(attrs={"class": "form-select"}),

             # Inputs -> form-control
            "valid_until": forms.TextInput(attrs={
                "class": "form-control datepicker",
                "autocomplete": "off",
                "placeholder": "YYYY-MM-DD",
            }),
            "note_1":      forms.Textarea(attrs={"rows": 6, "class": "form-control"}),

            # Hidden
            "date": forms.HiddenInput(),


        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) Filter CUSTOMER: roles.role='customer'
        if "customer" in self.fields:
            if PartnerRole is not None:
                cust_ids = PartnerRole.objects.filter(role__iexact="customer").values_list("partner_id", flat=True)
                self.fields["customer"].queryset = Partner.objects.filter(id__in=cust_ids).distinct()
            else:
                self.fields["customer"].queryset = Partner.objects.filter(roles__role__iexact="customer").distinct()

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

        # Filter AGENCY: roles.role='agency'
        if "sales_agency" in self.fields:
            if PartnerRole is not None:
                agency_ids = PartnerRole.objects.filter(role__iexact="agency").values_list("partner_id", flat=True)
                self.fields["sales_agency"].queryset = Partner.objects.filter(id__in=agency_ids).distinct()
            else:
                self.fields["sales_agency"].queryset = Partner.objects.filter(roles__role__iexact="agency").distinct()

        # default tanggal
        if not self.data.get("valid_until") and not self.initial.get("valid_until"):
            self.fields["valid_until"].initial = _date.today() + timedelta(days=7)
        if "date" in self.fields and not (self.data.get("date") or self.initial.get("date")):
            self.fields["date"].initial = _date.today()

        # currency default IDR kalau tersedia
        if "currency" in self.fields and not (self.data.get("currency") or self.initial.get("currency")):
            try:
                CurrencyModel = self.fields["currency"].queryset.model
                idr = CurrencyModel.objects.get(code="IDR")
                self.fields["currency"].initial = idr.pk
            except Exception:
                pass

            # === styling AdminLTE/Bootstrap ===
        from django.forms import HiddenInput
        for name, fld in self.fields.items():
            if not isinstance(fld.widget, HiddenInput):
                css = fld.widget.attrs.get("class", "")
                fld.widget.attrs["class"] = (css + " form-control").strip()
            
    def clean_date(self):
        return self.cleaned_data.get("date") or _date.today()


class QuotationLineForm(forms.ModelForm):
    # 2) Amount (Price × Qty) — hanya tampil (tidak disimpan)
    amount = forms.DecimalField(
        required=False,
        label="Amount",
        decimal_places=2,
        max_digits=18,
        widget=forms.TextInput(attrs={"readonly": "readonly"})
    )

    class Meta:
        model = SalesQuotationLine
        fields = ["origin", "destination", "description", "qty", "uom", "price", "amount"]

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.forms import HiddenInput
        for name, fld in self.fields.items():
            if not isinstance(fld.widget, HiddenInput):
                css = fld.widget.attrs.get("class", "")
                fld.widget.attrs["class"] = (css + " form-control").strip()



class BaseLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # minimal 1 baris memiliki data
        has_any = False
        for f in self.forms:
            cd = getattr(f, "cleaned_data", {}) or {}
            if cd.get("DELETE"):
                continue
            if any(cd.get(k) for k in ("origin", "destination", "description", "qty", "uom", "price")):
                has_any = True
                break
        if not has_any:
            raise forms.ValidationError("Minimal satu line harus diisi.")
