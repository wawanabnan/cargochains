from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from sales.models import SalesConfig
from sales.forms.sales_config import SalesConfigForm


class SalesConfigView(LoginRequiredMixin, View):
    template_name = "sales/sales_config.html"

    def get(self, request):
        cfg = SalesConfig.get_solo()
        form = SalesConfigForm(instance=cfg)
        return render(request, self.template_name, {"form": form, "cfg": cfg})

    def post(self, request):
        cfg = SalesConfig.get_solo()
        form = SalesConfigForm(request.POST, instance=cfg)

        if not form.is_valid():
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"ok": False, "message": "Form tidak valid.", "errors": form.errors},
                    status=400,
                )
            return render(request, self.template_name, {"form": form, "cfg": cfg})

        form.save()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})

        return render(request, self.template_name, {"form": SalesConfigForm(instance=cfg), "cfg": cfg})
