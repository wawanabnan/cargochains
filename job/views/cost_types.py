from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from job.models.costs import JobCostType
from job.forms.cost_types  import JobCostTypeForm


def is_accounting(user):
    return user.is_superuser or user.groups.filter(name__in=["Accounting", "Finance"]).exists()


class AccountingOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return is_accounting(self.request.user)


class CostTypeListView(LoginRequiredMixin, AccountingOnlyMixin, ListView):
    model = JobCostType
    template_name = "cost_types/list.html"
    context_object_name = "items"
    paginate_by = 20


class CostTypeCreateView(LoginRequiredMixin, AccountingOnlyMixin, CreateView):
    model = JobCostType
    form_class = JobCostTypeForm
    template_name = "cost_types/form.html"
    success_url = reverse_lazy("jobs:cost_type_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw


class CostTypeUpdateView(LoginRequiredMixin, AccountingOnlyMixin, UpdateView):
    model = JobCostType
    form_class = JobCostTypeForm
    template_name = "cost_types/form.html"
    success_url = reverse_lazy("jobs:cost_type_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw
