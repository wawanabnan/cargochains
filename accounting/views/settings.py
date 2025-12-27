from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import UpdateView

from accounting.models.settings import AccountingSettings
from accounting.forms.settings import AccountingSettingsForm


class AccountingSettingsUpdateView(LoginRequiredMixin, UpdateView):
    model = AccountingSettings
    form_class = AccountingSettingsForm
    template_name = "settings/form.html"

    def get_object(self, queryset=None):
        # singleton pk=1
        obj, _ = AccountingSettings.objects.get_or_create(pk=1)
        return obj

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Accounting settings updated.")
        return resp

    def get_success_url(self):
        return reverse("accounting:settings")
