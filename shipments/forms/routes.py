# shipments/forms/routes.py
from django import forms
from django.db.models import Max
from shipments.models import ShipmentRoute, TransportationAsset


# ✅ 1️⃣ Tambahkan ini SEBELUM ShipmentRouteForm
class AssetChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [obj.identifier]
        if getattr(obj, "type", None):
            parts.append(getattr(obj.type, "code", None) or getattr(obj.type, "name", None))
        if getattr(obj, "carrier", None) and getattr(obj.carrier, "name", None):
            parts.append(obj.carrier.name)
        return " — ".join([p for p in parts if p])


# ✅ 2️⃣ Baru class ShipmentRouteForm
class ShipmentRouteForm(forms.ModelForm):
    transportation_asset = AssetChoiceField(
        queryset=TransportationAsset.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm",
            "id": "id_transportation_asset",
        }),
        label="Transportation Asset",
    )

    class Meta:
        model = ShipmentRoute
        fields = [
            "order",
            "origin", "origin_text",
            "destination", "destination_text",
            "planned_departure", "planned_arrival",
            "transportation_type", "transportation_asset",
            "distance_km", "status",
            "driver_info",
        ]
        widgets = {
            "origin": forms.HiddenInput(),
            "destination": forms.HiddenInput(),
            "origin_text": forms.TextInput(attrs={
                "class": "form-control form-control-sm ac-location",
                "data-target": "origin",
                "placeholder": "Type & pick…",
            }),
            "destination_text": forms.TextInput(attrs={
                "class": "form-control form-control-sm ac-location",
                "data-target": "destination",
                "placeholder": "Type & pick…",
            }),
            "planned_departure": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control form-control-sm"
            }),
            "planned_arrival": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control form-control-sm"
            }),
            "transportation_type": forms.Select(attrs={
                "class": "form-select form-select-sm",
                "id": "route-transportation-type"
            }),
            "distance_km": forms.NumberInput(attrs={
                "step": "0.01",
                "class": "form-control form-control-sm"
            }),
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "driver_info": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Nama sopir & no. kendaraan"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default kosong: tunggu type dipilih
        self.fields["transportation_asset"].queryset = TransportationAsset.objects.none()

        # Ambil type dari POST (ADD/invalid) atau dari instance (EDIT)
        type_id = (self.data.get("transportation_type")
                   or getattr(getattr(self.instance, "transportation_type", None), "id", None))

        if type_id:
            self.fields["transportation_asset"].queryset = (
                TransportationAsset.objects.filter(type_id=type_id, active=True).order_by("identifier")
            )
        else:
            # EDIT tanpa type terdeteksi → minimal tampilkan asset yang sedang dipakai
            cur = getattr(self.instance, "transportation_asset", None)
            if cur:
                self.fields["transportation_asset"].queryset = TransportationAsset.objects.filter(pk=cur.pk)


    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.order:
            last = ShipmentRoute.objects.filter(shipment=obj.shipment).aggregate(m=Max("order"))["m"] or 0
            obj.order = last + 1
        if commit:
            obj.save()
        return obj
