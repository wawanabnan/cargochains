from django import forms
from core.models.settings import CoreSetting  # sesuaikan path
from core.models.currencies import Currency     # sesuaikan path

CODE_MULTI = "ENABLE_MULTI_CURRENCY"
CODE_TAX = "ENABLE_TAX"
CODE_DEF_CUR = "DEFAULT_CURRENCY_CODE"
CODE_QVALID = "QUOTATION_VALID_DAY"
CODE_SFEE = "SALES_FEE_PERCENT"
CODE_JOB_COST = "ENABLE_JOB_COST"
CODE_AUTO_JOURNAL = "ENABLE_AUTO_JOURNAL"


def _get_setting(code: str) -> CoreSetting:
    obj, _ = CoreSetting.objects.get_or_create(code=code)
    return obj

class GeneralConfigForm(forms.Form):
    enable_multi_currency = forms.BooleanField(required=False)
    default_currency = forms.ModelChoiceField(
        queryset=Currency.objects.all().order_by("code"),
        required=False,
        empty_label="-- Select currency --",
    )
    enable_tax = forms.BooleanField(required=False)

    quotation_valid_day = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "inputmode": "numeric"})
    )

    sales_fee_percent = forms.IntegerField(
        required=True,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "inputmode": "numeric"})
    )
    enable_job_cost = forms.BooleanField(required=False)
    enable_auto_journal = forms.BooleanField(required=False)



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        s_multi = _get_setting(CODE_MULTI)
        s_tax = _get_setting(CODE_TAX)
        s_def = _get_setting(CODE_DEF_CUR)
        s_qv = _get_setting(CODE_QVALID)
        s_sf = _get_setting(CODE_SFEE)

        initial_multi = bool(s_multi.int_value or 0)
        initial_tax = bool(s_tax.int_value if s_tax.int_value is not None else 1)

        self.initial["enable_multi_currency"] = initial_multi
        self.initial["enable_tax"] = initial_tax

        code = (s_def.char_value or "IDR").strip() or "IDR"
        cur = Currency.objects.filter(code=code).first()
        if cur:
            self.initial["default_currency"] = cur

        self.initial["quotation_valid_day"] = s_qv.int_value if s_qv.int_value is not None else 14
        self.initial["sales_fee_percent"] = s_sf.int_value if s_sf.int_value is not None else 20

        s_job = _get_setting(CODE_JOB_COST)
        s_auto = _get_setting(CODE_AUTO_JOURNAL)

        self.initial["enable_job_cost"] = bool(s_job.int_value if s_job.int_value is not None else 1)
        self.initial["enable_auto_journal"] = bool(s_auto.int_value or 0)


    def clean(self):
        cleaned = super().clean()
        multi = bool(cleaned.get("enable_multi_currency"))
        cur = cleaned.get("default_currency")

        # multi ON -> default currency wajib
        if multi and not cur:
            self.add_error("default_currency", "Default currency wajib dipilih jika Multi Currency aktif.")

        return cleaned

    def save(self):
        multi = bool(self.cleaned_data.get("enable_multi_currency"))
        tax = bool(self.cleaned_data.get("enable_tax"))
        cur = self.cleaned_data.get("default_currency")
        qv = int(self.cleaned_data.get("quotation_valid_day"))
        sf = int(self.cleaned_data.get("sales_fee_percent"))

        _get_setting(CODE_MULTI).int_value = 1 if multi else 0
        _get_setting(CODE_TAX).int_value = 1 if tax else 0

        # multi OFF -> paksa IDR
        _get_setting(CODE_DEF_CUR).char_value = "IDR" if not multi else cur.code

        _get_setting(CODE_QVALID).int_value = qv
        _get_setting(CODE_SFEE).int_value = sf

        _get_setting(CODE_MULTI).save(update_fields=["int_value"])
        _get_setting(CODE_TAX).save(update_fields=["int_value"])
        _get_setting(CODE_DEF_CUR).save(update_fields=["char_value"])
        _get_setting(CODE_QVALID).save(update_fields=["int_value"])
        _get_setting(CODE_SFEE).save(update_fields=["int_value"])
