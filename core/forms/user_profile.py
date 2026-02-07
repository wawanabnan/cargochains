# core/forms/user_profile.py
from django import forms
from core.models.user_profile import UserProfile
from django.contrib.auth import get_user_model
from core.models.user_profile import UserProfile

User = get_user_model() 
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["title", "signature"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Job Title / Position",
            }),
            "signature": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
        }

    def clean_username(self):
            username = (self.cleaned_data["username"] or "").strip()

            username = username.lower()
            if len(username) < 4:
                raise forms.ValidationError("Username minimal 4 karakter.")

            if self.user and username != self.user.username:
                exists = User.objects.filter(username=username).exclude(pk=self.user.pk).exists()
                if exists:
                    raise forms.ValidationError("Username sudah dipakai user lain.")

            return username


    def save(self):
        u = self.user
        u.first_name = (self.cleaned_data.get("first_name") or "").strip()
        u.last_name = (self.cleaned_data.get("last_name") or "").strip()
        u.username = self.cleaned_data["username"]
        u.save(update_fields=["first_name", "last_name", "username"])

        profile, _ = UserProfile.objects.get_or_create(user=u)  # ✅ safe
        profile.title = (self.cleaned_data.get("title") or "").strip()

        sig = self.cleaned_data.get("signature")
        if sig:
            profile.signature = sig

        profile.save()
        return u
