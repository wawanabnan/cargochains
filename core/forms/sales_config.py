from django import forms
from core.services.config_loader import load_sales_labels
from core.models.currencies import Currency


class SalesConfigForm(forms.Form):

    # ===== BASIC =====
    default_currency = forms.ModelChoiceField(
        queryset=Currency.objects.none(),  # ✅ JANGAN None
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm js-focus-select"
        })
    )

    quote_valid_day = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "0"
        })
    )

    sales_fee_percent = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm js-fee",
            "placeholder": "0,00"
        })
    )

    customer_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-sm js-tinymce",
            "rows": 8
        })
    )

    sla = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-sm js-tinymce",
            "rows": 8
        })
    )

    # ===== TAX =====
    tax_mode = forms.ChoiceField(
        required=True,
        choices=[],
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm js-focus-select"
        })
    )

    tax_apply_to = forms.ChoiceField(
        required=True,
        choices=[],
        widget=forms.Select(attrs={
            "class": "form-select form-select-sm js-focus-select"
        })
    )

    tax_auto_apply = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
            "role": "switch"
        })
    )

    # =======================
    # ✅ INIT (INI YANG HILANG)
    # =======================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---- Currency queryset ----
        self.fields["default_currency"].queryset = (
            Currency.objects.all().order_by("code")
        )

        labels = load_sales_labels()

        # ---- TAX MODE ----
        mode_cfg = labels.get("tax_mode") or {}

        def _mode_label(key, fallback):
            v = mode_cfg.get(key) or {}
            return v.get("label", fallback) if isinstance(v, dict) else fallback

        def _mode_help(key, fallback=""):
            v = mode_cfg.get(key) or {}
            return v.get("help", fallback) if isinstance(v, dict) else fallback

        self.fields["tax_mode"].choices = [
            ("allow_override", _mode_label("allow_override", "Allow override")),
            ("service_only",   _mode_label("service_only", "Service only")),
            ("manual_only",    _mode_label("manual_only", "Manual only")),
        ]

        self.tax_mode_help = {
            "allow_override": _mode_help("allow_override"),
            "service_only": _mode_help("service_only"),
            "manual_only": _mode_help("manual_only"),
        }

        # ---- TAX APPLY TO ----
        apply_cfg = labels.get("tax_apply_to") or {}

        def _apply_label(key, fallback):
            v = apply_cfg.get(key)
            return v if isinstance(v, str) and v.strip() else fallback

        self.fields["tax_apply_to"].choices = [
            ("quotation", _apply_label("quotation", "Quotation lines")),
            ("invoice",   _apply_label("invoice", "Invoice lines")),
            ("both",      _apply_label("both", "Both")),
        ]
