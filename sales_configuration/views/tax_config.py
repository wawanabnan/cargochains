from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from core.models.taxes import Tax
from sales_configuration.forms.tax_policy import SalesTaxConfigForm
from sales_configuration.models import SalesTaxPolicy


class SalesTaxConfigView(LoginRequiredMixin, View):
    template_name = "tax_config.html"

    def get(self, request):
        module = request.GET.get("module", "INVOICE")
        form = SalesTaxConfigForm(module=module)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        module = request.POST.get("module")
        form = SalesTaxConfigForm(request.POST, module=module)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        selected_taxes = form.cleaned_data["taxes"]
        default_tax = form.cleaned_data["default_tax"]

        # nonaktifkan semua dulu
        SalesTaxPolicy.objects.filter(module=module).update(is_active=False, is_default=False)

        # aktifkan yang dipilih
        for tax in selected_taxes:
            SalesTaxPolicy.objects.update_or_create(
                module=module,
                tax=tax,
                defaults={"is_active": True}
            )

        # set default
        if default_tax:
            SalesTaxPolicy.objects.update_or_create(
                module=module,
                tax=default_tax,
                defaults={"is_active": True, "is_default": True}
            )

        messages.success(request, "Sales tax configuration berhasil disimpan.")
        return redirect(f"{request.path}?module={module}")
