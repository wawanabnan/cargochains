from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView

from core.models.setup import SetupState


@login_required
def password_change_required(request):
    return render(request, "core/password_change_required.html", {})


class InitialAdminPasswordChangeView(PasswordChangeView):
    template_name = "core/password_change_form.html"

    def get_success_url(self):
        return reverse("core:password_change_done")


class InitialAdminPasswordChangeDoneView(TemplateView):
    template_name = "core/password_change_done.html"

    def dispatch(self, request, *args, **kwargs):
        state = SetupState.objects.first()
        if state and state.initial_admin_user_id == request.user.id:
            state.initial_admin_password = None
            state.force_password_change = False
            state.save(update_fields=["initial_admin_password", "force_password_change", "updated_at"])
        return super().dispatch(request, *args, **kwargs)
