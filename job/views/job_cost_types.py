from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from job.models.job_costs import JobCostType
from job.forms.job_cost_types  import JobCostTypeForm


from django.shortcuts import redirect
from django.contrib import messages
import json
import csv
from django.utils.safestring import mark_safe
from django.http import HttpResponse


def cost_type_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="cost_types.csv"'

    writer = csv.writer(
        response,
        delimiter=";",        # ✅ SEMICOLON
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow([
        "code",
        "name",
        "cost_group",
        "requires_vendor",
        "is_active",
        "sort_order",
    ])

    for obj in JobCostType.objects.all().order_by("sort_order", "code"):
        writer.writerow([
            obj.code,
            obj.name,
            obj.cost_group,
            int(obj.requires_vendor),
            int(obj.is_active),
            obj.sort_order,
        ])

    return response


def cost_type_import(request):
    if request.method != "POST":
        return redirect("job:cost_type_list")

    file = request.FILES.get("file")
    if not file:
        messages.error(request, "File tidak ditemukan.")
        return redirect("job:cost_type_list")

    decoded = file.read().decode("utf-8").splitlines()
    reader = csv.DictReader(
        decoded,
        delimiter=";",        # ✅ SEMICOLON
    )

    created, updated = 0, 0

    for row in reader:
        obj, is_created = JobCostType.objects.update_or_create(
            code=row["code"].strip(),
            defaults={
                "name": row.get("name", ""),
                "cost_group": row.get("cost_group", ""),
                "requires_vendor": row.get("requires_vendor") in ("1", "true", "True"),
                "is_active": row.get("is_active") in ("1", "true", "True"),
                "sort_order": int(row.get("sort_order") or 0),
            },
        )
        created += int(is_created)
        updated += int(not is_created)

    messages.success(
        request,
        f"Import selesai. Created: {created}, Updated: {updated}"
    )

    return redirect("job:cost_type_list")



def is_accounting(user):
    return user.is_superuser or user.groups.filter(name__in=["Accounting", "Finance"]).exists()


class AccountingOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return is_accounting(self.request.user)


class CostTypeListView(LoginRequiredMixin, AccountingOnlyMixin, ListView):
    model = JobCostType
    template_name = "cost_types/list.html"
    context_object_name = "items"
    paginate_by = 10


class CostTypeCreateView(LoginRequiredMixin, AccountingOnlyMixin, CreateView):
    model = JobCostType
    form_class = JobCostTypeForm
    template_name = "cost_types/form.html"
    success_url = reverse_lazy("job:cost_type_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw


class CostTypeUpdateView(LoginRequiredMixin, AccountingOnlyMixin, UpdateView):
    model = JobCostType
    form_class = JobCostTypeForm
    template_name = "cost_types/form.html"
    success_url = reverse_lazy("job:cost_type_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw



