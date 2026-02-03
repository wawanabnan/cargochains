from django.shortcuts import render, redirect
from core.models.setup import SetupState

def setup_done(request):
    state = SetupState.objects.filter(id=1).first()
    if not state or not state.is_completed:
        return redirect("core:welcome")

    # kalau sudah pernah lihat, jangan render lagi
    if request.session.get("setup_done_shown"):
        return redirect("account:dashboard")  # atau ke login kalau belum auth

    request.session["setup_done_shown"] = True
    return render(request, "setup/done.html")
