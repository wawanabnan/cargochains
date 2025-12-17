from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from sales_configuration.forms.tax_policy import SalesTaxConfigForm


class SalesConfigView(LoginRequiredMixin, View):
    template_name = "config.html"

    def get(self, request):
        module = request.GET.get("module", "INVOICE")

        ctx = {
            "module": module,
            "tax_form": SalesTaxConfigForm(module=module),
            # next (placeholder)
            "payment_form": None,
            "defaults_form": None,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        # card mana yang disave?
        action = request.POST.get("action", "")
        module = request.POST.get("module", "INVOICE")

        if action == "save_tax":
            tax_form = SalesTaxConfigForm(request.POST, module=module)
            if tax_form.is_valid():
                # pakai logic save yang sudah ada di view tax_config om
                # (kalau om belum punya helper save, aku tulis di bawah)
                from sales_configuration.models import SalesTaxPolicy
                selected_taxes = tax_form.cleaned_data["taxes"]
                default_tax = tax_form.cleaned_data["default_tax"]

                # reset module dulu
                SalesTaxPolicy.objects.filter(module=module).update(is_active=False, is_default=False)

                # aktifkan selected
                for tax in selected_taxes:
                    SalesTaxPolicy.objects.update_or_create(
                        module=module,
                        tax=tax,
                        defaults={"is_active": True, "is_default": False},
                    )

                # set default (auto aktif)
                if default_tax:
                    SalesTaxPolicy.objects.update_or_create(
                        module=module,
                        tax=default_tax,
                        defaults={"is_active": True, "is_default": True},
                    )

                messages.success(request, "Tax configuration berhasil disimpan.")
                return redirect(f"{request.path}?module={module}")

            # invalid → render lagi dengan error
            ctx = {
                "module": module,
                "tax_form": tax_form,
                "payment_form": None,
                "defaults_form": None,
            }
            messages.error(request, "VALIDATION ERROR — tax configuration.")
            return render(request, self.template_name, ctx)

        # default: balik lagi
        messages.error(request, "Aksi tidak valid.")
        return redirect(f"{request.path}?module={module}")
