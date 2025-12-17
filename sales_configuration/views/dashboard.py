from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class ConfigDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
