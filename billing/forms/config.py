from django import forms
from django_summernote.widgets import SummernoteWidget
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from billing.models.config import BillingConfig

User = get_user_model()


class BillingConfigForm(forms.ModelForm):

    class Meta:
        model = BillingConfig
        fields = "__all__"

        widgets = {

            # ===== BANK =====
            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_number": forms.TextInput(attrs={"class": "form-control"}),
            "swift_code": forms.TextInput(attrs={"class": "form-control"}),
            "bank_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

        
            # ===== SIGNATURE =====
            "signature_mode": forms.Select(attrs={"class": "form-select"}),
            "signature_name": forms.TextInput(attrs={"class": "form-control"}),
            "signature_title": forms.TextInput(attrs={"class": "form-control"}),
            "signature_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "signature_user": forms.Select(attrs={"class": "form-select"}),
            "auto_show_signature": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            # ===== SUMMERNOTE =====
            "default_customer_note": SummernoteWidget(),
            "default_terms_conditions": SummernoteWidget(),
            "default_footer_note": SummernoteWidget(),
        }

    # ============================================
    # INIT
    # ============================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter hanya user tertentu
        if "signature_user" in self.fields:
            self.fields["signature_user"].queryset = User.objects.filter(
                groups__name__in=["Finance", "Manager"]
            ).distinct()

    # ============================================
    # VALIDATION
    # ============================================

    def clean(self):
        cleaned_data = super().clean()

        mode = cleaned_data.get("signature_mode")
        signature_user = cleaned_data.get("signature_user")
        signature_image = cleaned_data.get("signature_image")

        if mode == BillingConfig.SIGNATURE_USER:
            if not signature_user:
                raise ValidationError(
                    {"signature_user": "Please select a user for USER signature mode."}
                )

        if mode == BillingConfig.SIGNATURE_MANUAL:
            # kalau belum pernah upload dan sekarang juga kosong
            if not signature_image and not self.instance.signature_image:
                raise ValidationError(
                    {"signature_image": "Please upload signature image in MANUAL mode."}
                )

        return cleaned_data