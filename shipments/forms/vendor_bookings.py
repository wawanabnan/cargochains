from datetime import date, timedelta

from django import forms
from django.forms import inlineformset_factory

from shipments.models.vendor_bookings import VendorBooking, VendorBookingLine
from job.models.job_orders import JobOrder
from job.models.costs import JobCostType


class VendorBookingForm(forms.ModelForm):
    class Meta:
        model = VendorBooking
        fields = [
            "number",
            "booking_date",
            "job_order",
            "vendor",
            "service",

            "origin_location",
            "origin_text",
            "destination_location",
            "destination_text",

            "pickup_note",
            "delivery_note",

            "etd",
            "eta",
            "currency",
            "payment_term",
            "source_type",
            "remarks",
            "status",
        ]
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 2, "class": "form-control form-control-sm"}),
            "pickup_note": forms.Textarea(attrs={"rows": 2, "class": "form-control form-control-sm"}),
            "delivery_note": forms.Textarea(attrs={"rows": 2, "class": "form-control form-control-sm"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ styling
        for name, f in self.fields.items():
            f.widget.attrs.setdefault("class", "form-control form-control-sm")

        # ✅ Batasi dropdown berat (optional, tapi bikin halaman nggak lemot)
        # Job Order: ambil yang recent saja (90 hari)
        if "job_order" in self.fields:
            since = date.today() - timedelta(days=90)
            qs = self.fields["job_order"].queryset
            # sesuaikan bila field JO berbeda
            if hasattr(qs.model, "job_date"):
                qs = qs.filter(job_date__gte=since)
            elif hasattr(qs.model, "created_at"):
                qs = qs.filter(created_at__date__gte=since)
            self.fields["job_order"].queryset = qs.order_by("-id")[:300]

        # Vendor/Location bisa besar juga → batasi (sementara; nanti idealnya autocomplete)
        if "vendor" in self.fields:
            self.fields["vendor"].queryset = self.fields["vendor"].queryset.order_by("name")[:500]

        if "origin_location" in self.fields:
            self.fields["origin_location"].queryset = self.fields["origin_location"].queryset.order_by("name")[:500]
        if "destination_location" in self.fields:
            self.fields["destination_location"].queryset = self.fields["destination_location"].queryset.order_by("name")[:500]


class _VendorBookingLineForm(forms.ModelForm):
    class Meta:
        model = VendorBookingLine
        fields = [
               "cost_type",
                "description",
                "qty",
                "uom",
                "unit_price",
                "estimated_tax",
                "estimated_tax_rate",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ HANYA COST TYPE YANG PERLU VENDOR (internal tidak muncul)
        self.fields["cost_type"].queryset = (
            JobCostType.objects
            .filter(is_active=True, requires_vendor=True)
            .order_by("sort_order", "name")
        )

        # styling
        for name, f in self.fields.items():
            f.widget.attrs.setdefault("class", "form-control form-control-sm")

        self.fields["description"].widget.attrs.setdefault("placeholder", "Keterangan (optional)")


VendorBookingLineFormSet = inlineformset_factory(
    VendorBooking,
    VendorBookingLine,
    form=_VendorBookingLineForm,
    extra=1,
    can_delete=True,
)
