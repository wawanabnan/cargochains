from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from core.forms.profile_modal import ProfileModalForm
from core.models.user_profile import UserProfile


class ProfileModalView(LoginRequiredMixin, View):
    template_name = "core/user_profiles/modal_form.html"

    
    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)  # ✅ ensure exists
        form = ProfileModalForm(user=request.user)
        return render(request, self.template_name, {"form": form})
    
class ProfileModalSubmitView(LoginRequiredMixin, View):
    template_name = "core/profile_modal_form.html"

    def post(self, request):
        UserProfile.objects.get_or_create(user=request.user)  # ✅ ensure exists
        form = ProfileModalForm(request.POST, request.FILES, user=request.user)

        if not form.is_valid():
            html = render(request, self.template_name, {"form": form}).content.decode("utf-8")
            return JsonResponse({"ok": False, "html": html}, status=400)

        form.save()

        # jangan akses request.user.profile sebelum ensure exists (sudah)
        sig = getattr(request.user.profile, "signature", None)
        sig_url = sig.url if sig else ""

        display_name = (request.user.get_full_name() or "").strip() or request.user.username
        return JsonResponse({"ok": True, "signature_url": sig_url, "display_name": display_name})
