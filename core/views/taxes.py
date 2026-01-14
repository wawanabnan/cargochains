from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.models.taxes import Tax, TaxCategory
from core.forms.taxes import TaxForm, TaxCategoryForm
from django.http import JsonResponse
from django.views import View 


class TaxListView(LoginRequiredMixin, ListView):
    model = Tax
    template_name = "taxes/tax_list.html"
    context_object_name = "taxes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Tax.objects.select_related("category", "output_account", "input_account")
            .order_by("category__code", "name")
        )

        q = (self.request.GET.get("q") or "").strip()
        active = self.request.GET.get("active")

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(category__code__icontains=q)
            )

        if active in ("0", "1"):
            qs = qs.filter(is_active=(active == "1"))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["active"] = self.request.GET.get("active", "")
        return ctx


class TaxCreateView(LoginRequiredMixin, CreateView):
    model = Tax
    form_class = TaxForm
    template_name = "taxes/form.html"
    success_url = reverse_lazy("core:tax_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        # TODO: ambil chart_year aktif jika sudah ada setting
        # kw["chart_year"] = ...
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Tax berhasil dibuat.")
        return super().form_valid(form)


class TaxUpdateView(LoginRequiredMixin, UpdateView):
    model = Tax
    form_class = TaxForm
    template_name = "taxes/form.html"
    success_url = reverse_lazy("core:tax_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        # TODO: ambil chart_year aktif jika sudah ada setting
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Tax berhasil diupdate.")
        return super().form_valid(form)


class TaxDeleteView(LoginRequiredMixin, DeleteView):
    model = Tax
    template_name = "core/taxes/tax_confirm_delete.html"
    success_url = reverse_lazy("core:tax_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Tax berhasil dihapus.")
        return super().delete(request, *args, **kwargs)


# OPTIONAL: CRUD TaxCategory (kalau om mau sekalian)
class TaxCategoryListView(LoginRequiredMixin, ListView):
    model = TaxCategory
    template_name = "taxes/category_list.html"
    context_object_name = "categories"
    paginate_by = 20
    ordering = ["code"]


class TaxCategoryCreateView(LoginRequiredMixin, CreateView):
    model = TaxCategory
    form_class = TaxCategoryForm
    template_name = "taxes/category_form.html"
    success_url = reverse_lazy("core:tax_category_list")


class TaxCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = TaxCategory
    form_class = TaxCategoryForm
    template_name = "taxes/category_form.html"
    success_url = reverse_lazy("core:tax_category_list")


class TaxCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = TaxCategory
    template_name = "taxes/category_confirm_delete.html"
    success_url = reverse_lazy("core:tax_category_list")

class TaxAutocompleteView(View):
    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        ids = request.GET.getlist("ids[]")

        qs = Tax.objects.filter(
            is_active=True,
            category__code="PPN",   # 🔥 KUNCI DI SINI
        ).order_by("name")

        # preload selected (edit mode)
        if ids:
            qs = qs.filter(id__in=ids)

        # search
        elif q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q)
            )

        qs = qs[:20]

        def fmt_rate(t: Tax) -> str:
            r = t.rate or 0
            s = f"{r.normalize():f}" if hasattr(r, "normalize") else str(r)
            s = s.rstrip("0").rstrip(".") if "." in s else s
            return f"{s}%"

        results = [
            {
                "id": t.id,
                "text": fmt_rate(t),   # tampil di dropdown & selected: "11%"
                "title": t.name,       # tooltip: "PPN 11%"
                # optional kalau mau:
                # "code": t.code,
            }
            for t in qs
        ]
        return JsonResponse({"results": results})
