from django.shortcuts import render, redirect
from django.urls import reverse
from core.models.setup import SetupState
from core.services.bootstrap import ensure_initial_admin


def welcome(request):
    # kalau sudah login, biarkan middleware setup/wizard yang handle
    if request.user.is_authenticated:
        return redirect("/")

    state = SetupState.objects.first()
    ctx = {
        "state": state,
    }
    return render(request, "core/welcome.html", ctx)
