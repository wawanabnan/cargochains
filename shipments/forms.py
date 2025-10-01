from django import forms
from .models import ShipmentStatusLog

class ShipmentStatusLogForm(forms.ModelForm):
    class Meta:
        model = ShipmentStatusLog
        fields = ["status", "event_time", "note"]
        widgets = {
            "event_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

# opsional: dipakai untuk tombol cepat (Book/In Transit/Delivered/Cancel)
class ShipmentQuickActionForm(forms.Form):
    ACTIONS = [
        ("BOOKED", "Book"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancel"),
    ]
    action = forms.ChoiceField(choices=ACTIONS)
