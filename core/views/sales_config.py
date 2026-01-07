# core/views/sales_settings.py
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View


try:
    from core.models.currencies import Currency
except Exception:
    from core.models import Currency

try:
    from core.models.taxes import Tax
except Exception:
    try:
        from core.models import Tax
    except Exception:
        Tax = None

from core.models.settings import CoreSetting
from core.services.core_settings import get_setting, set_setting
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from core.forms.sales_config import SalesConfigForm
from core.services.core_settings import get_setting, set_setting





def _pick_default_currency_obj():
    # prioritas IDR
    obj = Currency.objects.filter(code="IDR").first()
    return obj or Currency.objects.order_by("code").first()


def _to_decimal_safe(s: str, default=Decimal("0.00")) -> Decimal:
    if s is None:
        return default
    s = str(s).strip()
    if not s:
        return default
    try:
        return Decimal(s)
    except InvalidOperation:
        return default



class SalesConfigView(LoginRequiredMixin, View):
    template_name = "settings/sales_config.html"

    def get_initial(self):
        return {
            "quote_valid_day": get_setting("sales", "QUOTATION_VALID_DAY", 0),
            "sales_fee_percent": get_setting("sales", "SALES_FEE_PERCENT", "0.00") or "0.00",
            "customer_notes": get_setting("sales", "CUSTOMER_NOTES", "") or "",
            "sla": get_setting("sales", "SLA", "") or "",
            "tax_mode": get_setting("sales", "TAX_MODE", "allow_override") or "allow_override",
            "tax_auto_apply": int(get_setting("sales", "TAX_AUTO_APPLY", 1) or 0) == 1,
            "tax_apply_to": get_setting("sales", "APPLY_TAX_TO", "both") or "both",
            # default_currency: isi sesuai logic om (FK lookup) kalau fieldnya ada
        }

    def get(self, request):
        form =SalesConfigForm(initial=self.get_initial())
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        form =SalesConfigForm(request.POST)
        if not form.is_valid():
            if is_ajax:
                return JsonResponse({"ok": False, "message": "Form invalid", "errors": form.errors}, status=400)
            return render(request, self.template_name, {"form": form})

        # currency: store code
        currency = form.cleaned_data.get("default_currency")
        set_setting("sales", "DEFAULT_CURRENCY_CODE", char_value=(currency.code if currency else "IDR"))

        # valid day
        valid_day = form.cleaned_data.get("quote_valid_day")
        set_setting("sales", "QUOTATION_VALID_DAY", int_value=(valid_day if valid_day is not None else 0))

        # fee from hidden raw
        fee_raw = (request.POST.get("sales_fee_percent_raw") or "").strip()
        fee = _to_decimal_safe(fee_raw, default=Decimal("0.00"))
        if fee < 0: fee = Decimal("0.00")
        if fee > 100: fee = Decimal("100.00")
        set_setting("sales", "SALES_FEE_PERCENT", char_value=f"{fee:.2f}")

        # TinyMCE text (gunakan text_value kalau ada)
        set_setting("sales", "CUSTOMER_NOTES", text_value=form.cleaned_data.get("customer_notes") or "")
        set_setting("sales", "SLA", text_value=form.cleaned_data.get("sla") or "")

        # ✅ Tax behavior only (no default tax, no available tax)
        set_setting("sales", "TAX_MODE", char_value=form.cleaned_data["tax_mode"])
        set_setting("sales", "TAX_AUTO_APPLY", int_value=(1 if form.cleaned_data.get("tax_auto_apply") else 0))
        set_setting("sales", "APPLY_TAX_TO", char_value=form.cleaned_data["tax_apply_to"])

        if is_ajax:
            return JsonResponse({"ok": True, "message": "Setting has been saved"})

        messages.success(request, "Sales Settings berhasil disimpan.")
        return redirect("core:sales_config")
