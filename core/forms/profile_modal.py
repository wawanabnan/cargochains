from django import forms
from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()

class ProfileModalForm(forms.Form):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={"class": "form-control"}))

    title = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    signature = forms.ImageField(required=False, widget=forms.ClearableFileInput(
        attrs={"class": "form-control", "accept": "image/png,image/jpeg"}
    ))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # initial values
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["username"].initial = user.username

            profile = getattr(user, "profile", None)
            if profile:
                self.fields["title"].initial = profile.title

    def clean_username(self):
        username = (self.cleaned_data["username"] or "").strip()
        if not username:
            raise forms.ValidationError("Username wajib diisi.")
        if self.user and username != self.user.username:
            exists = User.objects.filter(username=username).exclude(pk=self.user.pk).exists()
            if exists:
                raise forms.ValidationError("Username sudah dipakai user lain.")
        return username

    def save(self):
        # save User
        u = self.user
        u.first_name = (self.cleaned_data.get("first_name") or "").strip()
        u.last_name = (self.cleaned_data.get("last_name") or "").strip()
        u.username = self.cleaned_data["username"]
        u.save(update_fields=["first_name", "last_name", "username"])

        # save Profile
        p: UserProfile = u.profile
        p.title = (self.cleaned_data.get("title") or "").strip()
        sig = self.cleaned_data.get("signature")
        if sig:
            p.signature = sig
        p.save()
        return u
