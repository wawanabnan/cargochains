# shipments/forms/shipping_instruction.py
from django import forms
from shipments.models.shipping_instruction import ShippingInstructionDocument, SeaShippingInstructionDetail

class ShippingInstructionDocumentForm(forms.ModelForm):
    class Meta:
        model = ShippingInstructionDocument
        fields = [
            "letter_date",
            "status",
            "shipper_name", "shipper_address",
            "customer_name", "customer_address",
            "reference_no",
        ]
        widgets = {
            "letter_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "shipper_name": forms.TextInput(attrs={"class": "form-control"}),
            "shipper_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "customer_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "reference_no": forms.TextInput(attrs={"class": "form-control"}),
        }

class SeaShippingInstructionDetailForm(forms.ModelForm):
    class Meta:
        model = SeaShippingInstructionDetail
        fields = [
            "carrier_name", "vessel_name", "voyage_no",
            "pol", "pod", "final_destination",
            "etd", "eta",
            "special_instructions",
        ]
        widgets = {
            "carrier_name": forms.TextInput(attrs={"class": "form-control"}),
            "vessel_name": forms.TextInput(attrs={"class": "form-control"}),
            "voyage_no": forms.TextInput(attrs={"class": "form-control"}),
            "pol": forms.TextInput(attrs={"class": "form-control"}),
            "pod": forms.TextInput(attrs={"class": "form-control"}),
            "final_destination": forms.TextInput(attrs={"class": "form-control"}),
            "etd": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "eta": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "special_instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
