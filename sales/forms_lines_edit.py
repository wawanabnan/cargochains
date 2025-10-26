# sales/forms_line_edit.py
from django import forms
from . import models as m

class LineEditForm(forms.ModelForm):
    # Teks yang terlihat (buat autocomplete)
    origin_text = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class":"form-control form-control-sm js-origin-input",
        "placeholder":"Search origin…",
        "autocomplete":"off",
        "data-url":"/geo/locations/ajaxview/"
    }))
    destination_text = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class":"form-control form-control-sm js-dest-input",
        "placeholder":"Search destination…",
        "autocomplete":"off",
        "data-url":"/geo/locations/ajaxview/"
    }))

    class Meta:
        model = m.SalesQuotationLine
        fields = [
            "origin", "destination", "description", "uom", "qty", "price", "amount",
            "origin_text", "destination_text",
        ]
        widgets = {
            "origin":      forms.HiddenInput(),      # ← FK disimpan di hidden
            "destination": forms.HiddenInput(),      # ← FK disimpan di hidden
     
            "uom":         forms.Select(attrs={"class":"form-select form-select-sm line-uom"}),
            "description": forms.TextInput(attrs={"rows":2, "class":"form-control form-control-sm line-desc"}),
            "qty":         forms.NumberInput(attrs={"class":"form-control form-control-sm text-end line-qty"}),
            "price":       forms.NumberInput(attrs={"class":"form-control form-control-sm text-end line-price"}),
            "amount":      forms.NumberInput(attrs={"readonly":"readonly","class":"form-control form-control-sm text-end line-amount"}),
        }


        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Prefill teks dari instance supaya saat EDIT terlihat labelnya
            if self.instance and self.instance.pk:
                if self.instance.origin:
                    self.fields["origin_text"].initial = getattr(self.instance.origin, "name", str(self.instance.origin))
                if self.instance.destination:
                    self.fields["destination_text"].initial = getattr(self.instance.destination, "name", str(self.instance.destination))

from django.forms import BaseInlineFormSet

class LineEditFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        inst = form.instance
        # Isi initial text dari instance saat EDIT (GET)
        if not form.is_bound and inst and inst.pk:
            if inst.origin_id and "origin_text" in form.fields:
                form.fields["origin_text"].initial = getattr(inst.origin, "name", str(inst.origin))
            if inst.destination_id and "destination_text" in form.fields:
                form.fields["destination_text"].initial = getattr(inst.destination, "name", str(inst.destination))