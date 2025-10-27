# shipments/forms_routes.py
from django import forms
from django.forms import BaseInlineFormSet
from .. import models as m

class ShipmentRouteForm(forms.ModelForm):
    class Meta:
        model = m.ShipmentRoute
        fields = [
            "order",
            "origin", "origin_text",
            "destination", "destination_text",
            "planned_departure", "planned_arrival",
            "transportation_type", "transportation_asset",
            "distance_km", "status",
        ]
        widgets = {
            # FK disembunyikan -> akan diisi lewat autocomplete JS
            "origin": forms.HiddenInput(),
            "destination": forms.HiddenInput(),

            # Teks yang diketik user untuk cari lokasi (autocomplete)
            "origin_text": forms.TextInput(attrs={
                "placeholder": "Type to search origin...",
                "class": "form-control form-control-sm ac-location",
                "data-target": "origin",
            }),
            "destination_text": forms.TextInput(attrs={
                "placeholder": "Type to search destination...",
                "class": "form-control form-control-sm ac-location",
                "data-target": "destination",
            }),

            "planned_departure": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
            "planned_arrival": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
            "transportation_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "transportation_asset": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "distance_km": forms.NumberInput(attrs={"step": "0.01", "class": "form-control form-control-sm"}),
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        }

    def clean(self):
        cleaned = super().clean()
        # Modal: kita wajibkan origin/destination (ID) harus terisi (dipilih dari hasil autocomplete)
        if not cleaned.get("origin"):
            raise forms.ValidationError("Origin tidak dikenali. Pilih dari hasil pencarian.")
        if not cleaned.get("destination"):
            raise forms.ValidationError("Destination tidak dikenali. Pilih dari hasil pencarian.")

        etd = cleaned.get("planned_departure")
        eta = cleaned.get("planned_arrival")
        if etd and eta and etd > eta:
            raise forms.ValidationError("ETD tidak boleh lebih besar dari ETA.")
        return cleaned


class ShipmentRouteFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        active = [f for f in self.forms if not f.cleaned_data.get("DELETE", False)]
        if not active:
            raise forms.ValidationError("Minimal satu rute harus diisi.")
        # nomori otomatis
        for i, f in enumerate(active, start=1):
            f.cleaned_data["order"] = i
