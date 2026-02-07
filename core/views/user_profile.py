# core/views/profile.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View

from core.forms.user_profile import UserProfileForm

class UserProfileUpdateView(LoginRequiredMixin, View):
    template_name = "core/profile_form.html"

    def get(self, request):
        profile = request.user.profile
        form = UserProfileForm(instance=profile)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        profile = request.user.profile
        form = UserProfileForm(
            request.POST,
            request.FILES,   # 🔴 PENTING untuk upload
            instance=profile
        )

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        form.save()
        return redirect("profile_edit")  # sesuaikan URL
