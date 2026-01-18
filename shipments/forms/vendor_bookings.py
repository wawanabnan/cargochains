from django.db import models
from decimal import Decimal
from django import forms
from shipments.models.vendor_bookings import VendorBooking
from core.models.payment_terms import PaymentTerm
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError


discount_amount = models.DecimalField(
    max_digits=18,
    decimal_places=2,
    default=Decimal("0.00"),
    help_text="Discount amount (authoritative)"
)

from django import forms
from shipments.models.vendor_bookings import VendorBooking
from job.models.job_orders import JobOrder

class VendorBookingForm(forms.ModelForm):
    # -----------------------------
    # Header JSON fields (simple)
    # -----------------------------
    reference_no = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    shipper_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    consignee_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    notify_party_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))

    cargo_information = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 4}),
    )

    # SEA
    pol = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    pod = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    etd = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))
    eta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))

    # AIR
    origin_airport = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))
    dest_airport = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))

    # TRUCK
    pickup_location = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}))
    delivery_location = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}))
    pickup_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))
    delivery_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))

    class Meta:
        model = VendorBooking
        fields = [
            "job_order",
            "issued_date",
            "vendor",
            "booking_group",
            "payment_term",
            "currency",
            "idr_rate",
            "discount_amount",
            "letter_type",
            # numbers (readonly in __init__)
            "vb_number",
            "letter_number",
            'wht_rate'
        ]
        widgets = {
            "issued_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "job_order": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "vendor": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "booking_group": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "payment_term": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "currency": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "idr_rate": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "discount_amount": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
            "letter_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "vb_number": forms.TextInput(attrs={"class": "form-control form-control-sm", "readonly": "readonly"}),
            "letter_number": forms.TextInput(attrs={"class": "form-control form-control-sm", "readonly": "readonly"}),
            "idr_rate": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.000001"}),
            "wht_rate": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.000001"}),
            
       
        }

    # -----------------------------
    # Init: load header_json -> fields
    # -----------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # readonly numbers (safety)
        self.fields["vb_number"].disabled = True
        self.fields["letter_number"].disabled = True

        inst = getattr(self, "instance", None)
        data = (inst.header_json or {}) if (inst and inst.pk) else {}

        # populate json fields
        self.fields["reference_no"].initial = data.get("reference_no", "")
        self.fields["shipper_name"].initial = data.get("shipper_name", "")
        self.fields["consignee_name"].initial = data.get("consignee_name", "")
        self.fields["notify_party_name"].initial = data.get("notify_party_name", "")
        self.fields["cargo_information"].initial = data.get("cargo_information", "")

        # per type
        self.fields["pol"].initial = data.get("pol", "")
        self.fields["pod"].initial = data.get("pod", "")
        self.fields["etd"].initial = data.get("etd") or None
        self.fields["eta"].initial = data.get("eta") or None

        self.fields["origin_airport"].initial = data.get("origin_airport", "")
        self.fields["dest_airport"].initial = data.get("dest_airport", "")

        self.fields["pickup_location"].initial = data.get("pickup_location", "")
        self.fields["delivery_location"].initial = data.get("delivery_location", "")
        self.fields["pickup_date"].initial = data.get("pickup_date") or None
        self.fields["delivery_date"].initial = data.get("delivery_date") or None

        print(">>> VendorBookingForm LOADED, JobOrder count =", JobOrder.objects.count())

        # optional: auto-fill shipper from job_order when create
        if not (inst and inst.pk):
            job = self.initial.get("job_order") or self.data.get("job_order")
            # kalau mau auto-fill dari job, kita lakukan nanti (perlu lookup JobOrder)


        for name in self.fields:
            if "class" not in self.fields[name].widget.attrs:
                self.fields[name].widget.attrs["class"] = "form-control form-control-sm"
     

    # -----------------------------
    # Save: fields -> header_json
    # -----------------------------
    def save(self, commit=True):
        obj = super().save(commit=False)

        hdr = obj.header_json or {}
        # common
        hdr["reference_no"] = self.cleaned_data.get("reference_no", "") or ""
        hdr["shipper_name"] = self.cleaned_data.get("shipper_name", "") or ""
        hdr["consignee_name"] = self.cleaned_data.get("consignee_name", "") or ""
        hdr["notify_party_name"] = self.cleaned_data.get("notify_party_name", "") or ""
        hdr["cargo_information"] = self.cleaned_data.get("cargo_information", "") or ""

        # by letter_type
        lt = self.cleaned_data.get("letter_type") or obj.letter_type

        # SEA
        if lt == VendorBooking.LETTER_SEA_SI:
            hdr["pol"] = self.cleaned_data.get("pol", "") or ""
            hdr["pod"] = self.cleaned_data.get("pod", "") or ""
            hdr["etd"] = self.cleaned_data.get("etd").isoformat() if self.cleaned_data.get("etd") else ""
            hdr["eta"] = self.cleaned_data.get("eta").isoformat() if self.cleaned_data.get("eta") else ""

        # AIR
        elif lt == VendorBooking.LETTER_AIR_SLI:
            hdr["origin_airport"] = self.cleaned_data.get("origin_airport", "") or ""
            hdr["dest_airport"] = self.cleaned_data.get("dest_airport", "") or ""
            hdr["etd"] = self.cleaned_data.get("etd").isoformat() if self.cleaned_data.get("etd") else ""
            hdr["eta"] = self.cleaned_data.get("eta").isoformat() if self.cleaned_data.get("eta") else ""

        # TRUCK
        else:
            hdr["pickup_location"] = self.cleaned_data.get("pickup_location", "") or ""
            hdr["delivery_location"] = self.cleaned_data.get("delivery_location", "") or ""
            hdr["pickup_date"] = self.cleaned_data.get("pickup_date").isoformat() if self.cleaned_data.get("pickup_date") else ""
            hdr["delivery_date"] = self.cleaned_data.get("delivery_date").isoformat() if self.cleaned_data.get("delivery_date") else ""

        obj.header_json = hdr
        
        if commit:
            obj.save()
            self.save_m2m()
        return obj

    def clean(self):
        cleaned = super().clean()

        currency = cleaned.get("currency")
        idr_rate = cleaned.get("idr_rate")
        discount_amount = cleaned.get("discount_amount")

        if currency and idr_rate in (None, ""):
            self.add_error(
                "idr_rate",
                "IDR rate wajib diisi jika currency dipilih."
            )

        if not self.cleaned_data.get("idr_rate"):
            self.cleaned_data["idr_rate"] = Decimal("1")

        

        if discount_amount is not None and discount_amount < 0:
            self.add_error(
                "discount_amount",
                "Discount amount tidak boleh negatif."
            )

        return cleaned
    


from django import forms
from django.forms import inlineformset_factory

from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from core.models.taxes import Tax
from django.utils import timezone


class VendorBookingLineForm(forms.ModelForm):
    class Meta:
        model = VendorBookingLine
        fields = ["job_cost", "cost_type", "description", "qty", "uom", "unit_price", "amount", "sort_order", "is_active"]
        widgets = {
            "job_cost": forms.HiddenInput(),
            "cost_type": forms.HiddenInput(),  # auto-sync dari job_cost
            "description": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "qty": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "uom": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "amount": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "readonly": "readonly"}),
            "sort_order": forms.HiddenInput(),
            "is_active": forms.HiddenInput(),
            
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("job_cost"):
            raise forms.ValidationError("Job Cost wajib.")
        
        currency = cleaned.get("currency")
        idr_rate = cleaned.get("idr_rate")
        discount_amount = cleaned.get("discount_amount")

        # --- FIX currency/idr_rate ---
        cur_code = getattr(currency, "code", None) if currency else None

        if not idr_rate:
            # kalau currency kosong atau IDR -> default 1 (tanpa error)
            if (not currency) or (cur_code == "IDR"):
                cleaned["idr_rate"] = Decimal("1")
            else:
                # kalau bukan IDR (USD/EUR dst) -> wajib isi rate
                self.add_error("idr_rate", "IDR rate wajib diisi jika currency bukan IDR.")

        # --- discount validation ---
        if discount_amount is not None and discount_amount < 0:
            self.add_error("discount_amount", "Discount amount tidak boleh negatif.")

        return cleaned


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # field ini akan kita isi dari server / default
        if "job_order" in self.fields:
            self.fields["job_order"].required = False

        if "issued_date" in self.fields:
            self.fields["issued_date"].required = False
            if not self.initial.get("issued_date"):
                self.initial["issued_date"] = timezone.now().date()

        if "discount_amount" in self.fields:
            self.fields["discount_amount"].required = False
            if self.initial.get("discount_amount") in (None, ""):
                self.initial["discount_amount"] = Decimal("0")

        if "letter_type" in self.fields:
            self.fields["letter_type"].required = False
            if not self.initial.get("letter_type"):
                self.initial["letter_type"] = "TRUCK_TO"
 

VendorBookingLineFormSet = inlineformset_factory(
    parent_model=VendorBooking,
    model=VendorBookingLine,
    form=VendorBookingLineForm,
    extra=0,
    can_delete=False,
)