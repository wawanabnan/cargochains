from django import forms
from django.core.exceptions import ValidationError

from shipments.models.shipments import Shipment


class ShipmentCreateForm(forms.ModelForm):
    same_as_customer = forms.BooleanField(
        required=False,
        label="Shipper sama dengan Customer",
    )

    class Meta:
        model = Shipment
        fields = [
            "sales_service",
            "customer",
            "shipper",
            "consignee",
            # kalau ada:
            # "cargo_description",
            # "total_weight",
            # "total_volume",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in ["customer", "shipper", "consignee"]:
            self.fields[name].widget.attrs.update(
                {"class": "form-select js-partner-select"}
            )

    def clean(self):
        cleaned = super().clean()

        sales_service = cleaned.get("sales_service")
        customer = cleaned.get("customer")
        shipper = cleaned.get("shipper")
        consignee = cleaned.get("consignee")
        same_as_customer = cleaned.get("same_as_customer")

        errors = {}

        # Customer wajib
        if not customer:
            errors["customer"] = "Customer wajib diisi."

        # Shipper: kalau dicentang same_as_customer, pakai customer
        if same_as_customer:
            shipper = customer
            cleaned["shipper"] = customer
        else:
            if not shipper:
                errors["shipper"] = "Shipper wajib diisi."

        if not consignee:
            errors["consignee"] = "Consignee wajib diisi."

        # Validasi D2D: shipper & consignee harus punya alamat
        is_d2d = bool(sales_service and getattr(sales_service, "is_door_to_door", False))

        if is_d2d:
            if shipper and not getattr(shipper, "address", None):
                errors["shipper"] = "Alamat shipper wajib diisi untuk layanan Door to Door."
            if consignee and not getattr(consignee, "address", None):
                errors["consignee"] = "Alamat consignee wajib diisi untuk layanan Door to Door."

        if errors:
            raise ValidationError(errors)

        return cleaned

    def save(self, commit=True):
        instance: Shipment = super().save(commit=False)

        same_as_customer = self.cleaned_data.get("same_as_customer")
        customer = self.cleaned_data.get("customer")

        # Sekali lagi pastikan shipper = customer kalau dicentang
        if same_as_customer and customer:
            instance.shipper = customer

        if commit:
            instance.save()
        return instance
