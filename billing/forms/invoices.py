# sales/forms/invoices.py
from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from django import forms
from core.models.taxes import Tax
from billing.models.customer_invoice import Invoice,InvoiceLine
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django_summernote.widgets import SummernoteWidget

def _to_decimal_id(v):
    """
    Terima:
      - Indonesia: "1.000,00" / "1000,00"
      - Standar : "1000.00"
      - Integer : "1000"
    Return Decimal('1000.00')
    """
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None

    s = s.replace(" ", "")

    try:
        # Kalau ada koma => format Indonesia (titik ribuan, koma desimal)
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
            return Decimal(s)

        # Kalau tidak ada koma:
        # - Anggap "1000.00" itu format standar (titik = desimal) => BIARKAN
        # - Anggap "1.000" (tanpa koma) itu ribuan? (opsional) → biasanya tidak dipakai
        return Decimal(s)

    except (InvalidOperation, ValueError):
        return None



class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "customer",
            "invoice_date",
            "due_date",
            "currency",
            "payment_term",
            "subtotal_amount",
            "tax_amount",
            "total_amount",
            "idr_rate"
           
        ]

        widgets = {
            "job_order": forms.Select(attrs={"class": "form-select"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "payment_term": forms.Select(attrs={"class": "form-select"}),
            "invoice_date": forms.DateInput(attrs={"type": "date", "class": "form-control", "autocomplete": "off",}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control","autocomplete": "off",}),
             "customer_notes": SummernoteWidget(
                attrs={"summernote": {"height": "90px"}}
            ),
            "terms_conditions": SummernoteWidget(
                attrs={"summernote": {"height": "9px"}}
            ),        

            "idr_rate": forms.TextInput(attrs={
                "class": "form-control text-end js-idr-rate",
                "inputmode": "decimal",
                "autocomplete": "off",
                "readonly": "readonly",
            }) 
            
        }    



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # date
        for df in ("invoice_date", "due_date"):
            if df in self.fields:
                self.fields[df].widget = forms.DateInput(attrs={"type": "date"})

        # styling AdminLTE/Bootstrap
        for name, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            if isinstance(f.widget, forms.Select):
                f.widget.attrs["class"] = (css + " form-select form-select-sm").strip()
            else:
                if not isinstance(f.widget, forms.CheckboxInput):
                    f.widget.attrs["class"] = (css + " form-control form-control-sm").strip()

        # totals: display-only + jangan wajib
        for n in ("subtotal_amount", "tax_amount", "total_amount"):
            if n in self.fields:
                self.fields[n].required = False
                self.fields[n].initial = Decimal("0.00")
                self.fields[n].widget = forms.TextInput()  # biar aman kalau mau ditampilkan
                self.fields[n].widget.attrs.update({
                    "class": (self.fields[n].widget.attrs.get("class", "") + " form-control form-control-sm text-end").strip(),
                    "readonly": "readonly",
                    "autocomplete": "off",
                })


        


class InvoiceLineForm(forms.ModelForm):
    
    class Meta:
        model = InvoiceLine
        fields = ["description", "quantity", "price", "taxes"]
        widgets = {
            "description": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "autocomplete": "off",
            }),
            "quantity": forms.TextInput(attrs={
                "class": "form-control form-control-sm text-end js-num",
                "inputmode": "decimal",
                "autocomplete": "off",
            }),
            "price": forms.TextInput(attrs={
                "class": "form-control form-control-sm text-end js-num",
                "inputmode": "decimal",
                "autocomplete": "off",
            }),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "taxes" in self.fields:
            self.fields["taxes"].required = False
            self.fields["taxes"].widget = forms.CheckboxSelectMultiple()

            allowed = Tax.objects.filter(
                is_active=True,
                sales_policies__module="INVOICE",
                sales_policies__is_active=True,
            ).distinct().order_by("name")

            self.fields["taxes"].queryset = allowed
            

        invoice = getattr(self.instance, "invoice", None)

        if invoice and (
            invoice.tax_locked or
            invoice.status != Invoice.ST_DRAFT
        ):
            self.fields["taxes"].disabled = True
                

    def clean_quantity(self):
        v = self.cleaned_data.get("quantity")
        dec = _to_decimal_id(v)
        if dec is None:
            raise forms.ValidationError("Number Format is not valid.")
        return dec

    def clean_price(self):
        v = self.cleaned_data.get("price")
        dec = _to_decimal_id(v)
        if dec is None:
            raise forms.ValidationError("This field is required.")
        return dec

    

InvoiceLineFormSet = inlineformset_factory(
    Invoice,
    InvoiceLine,
    form=InvoiceLineForm,
    extra=0,        # ✅ ini yang mencegah "form kosong bawaan" bikin required error
    can_delete=True
)


