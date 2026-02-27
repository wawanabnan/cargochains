from django import forms
from billing.models.customer_receipt import CustomerReceipt
from billing.models.customer_invoice import Invoice

from accounting.models.settings import AccountingSettings
from accounting.models.chart import Account

class CustomerReceiptForm(forms.ModelForm):
    # tampil di UI, tapi tidak disimpan dari input user
    customer_display = forms.CharField(
        required=False,
        label="Customer",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "readonly": "readonly",
        }),
    )

    class Meta:
        model = CustomerReceipt
        fields = ["receipt_date", "invoice", "customer_display", "amount", "pph_withheld", "cash_account", "notes"]
        widgets = {
            "receipt_date": forms.DateInput(attrs={"class":"form-control form-control-sm", "type":"date"}),
            "invoice": forms.Select(attrs={"class":"form-select form-select-sm"}),
            "amount": forms.TextInput(attrs={"class":"form-control form-control-sm text-end"}),
            "pph_withheld": forms.TextInput(attrs={"class":"form-control form-control-sm text-end"}),
            "cash_account": forms.Select(attrs={"class":"form-select form-select-sm"}),
            "notes": forms.TextInput(attrs={"class":"form-control form-control-sm"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        inv = None
        if self.instance and getattr(self.instance, "invoice_id", None):
            inv = self.instance.invoice

        # kalau form dipost dan invoice dipilih, ambil dari data
        if not inv:
            try:
                inv_id = self.data.get("invoice")
                if inv_id:
                    # sesuaikan path
                    inv = Invoice.objects.select_related("customer").filter(pk=inv_id).first()
            except Exception:
                inv = None

        self.fields["customer_display"].initial = inv.customer.name if inv and inv.customer else ""
