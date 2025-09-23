from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from .forms import LoginForm
from .models import UserProfile

def user_login(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("account:dashboard")
    else:
        form = LoginForm()
    return render(request, "account/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("account:login")


@login_required
def dashboard(request):
    profile = getattr(request.user, "userprofile", None)
    return render(request, "account/dashboard.html", {"profile": profile})


@login_required
def users_list(request):
    users = UserProfile.objects.select_related("user").all()
    return render(request, "account/users_list.html", {"users": users})
