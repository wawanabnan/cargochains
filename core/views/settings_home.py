from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class SettingsHomeView(LoginRequiredMixin, TemplateView):
    template_name = "settings/home.html"
