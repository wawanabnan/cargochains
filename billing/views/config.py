from django.views.generic import UpdateView
from django.urls import reverse_lazy
from billing.models.config import BillingConfig
from billing.forms.config import BillingConfigForm


class BillingConfigUpdateView(UpdateView):
    model = BillingConfig
    form_class = BillingConfigForm
    template_name = "billing_config/form.html"
    success_url = reverse_lazy("billing:config")

    def get_object(self):
        return BillingConfig.get_solo()