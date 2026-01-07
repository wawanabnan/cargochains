from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from core.forms.company import CompanyForm
from core.models.company import CompanyProfile  # sesuaikan path


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    model = CompanyProfile
    form_class = CompanyForm
    template_name = "company/profile.html"
    success_url = reverse_lazy("core:setup_company")

    def get_object(self, queryset=None):
        obj = CompanyProfile.objects.first()
        if obj:
            return obj
        # auto-create minimal
        return CompanyProfile.objects.create(name="")

    def form_valid(self, form):
        messages.success(self.request, "Company settings berhasil disimpan.")
        return super().form_valid(form)
