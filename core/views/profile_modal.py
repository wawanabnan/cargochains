from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from core.forms.profile_modal import ProfileModalForm

class ProfileModalView(LoginRequiredMixin, View):
    template_name = "core/user_profiles/modal_form.html"

    def get(self, request):
        form = ProfileModalForm(user=request.user)
        return render(request, self.template_name, {"form": form})

class ProfileModalSubmitView(LoginRequiredMixin, View):
    template_name = "core/profile_modal_form.html"

    def post(self, request):
        form = ProfileModalForm(request.POST, request.FILES, user=request.user)

        if not form.is_valid():
            html = render(request, self.template_name, {"form": form}).content.decode("utf-8")
            return JsonResponse({"ok": False, "html": html}, status=400)

        form.save()

        # return fresh values for UI update (no reload)
        sig = getattr(getattr(request.user, "profile", None), "signature", None)
        sig_url = sig.url if sig else ""

        full = (request.user.get_full_name() or "").strip()
        name = full or request.user.username

        return JsonResponse({
            "ok": True,
            "signature_url": sig_url,
            "display_name": name,
            "username": request.user.username,
        })
