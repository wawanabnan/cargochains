# sales/forms_job_attachment.py
from django import forms
from .job_order_model import JobOrderAttachment


class JobOrderAttachmentForm(forms.ModelForm):
    class Meta:
        model = JobOrderAttachment
        fields = ["file", "description"]
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Keterangan file (opsional)"}
            ),
        }
