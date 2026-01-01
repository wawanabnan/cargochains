from django.shortcuts import render, redirect
from core.models.setup import SetupState

def setup_done(request):
    state = SetupState.objects.filter(id=1).first()
    if not state or not state.is_completed:
        return redirect("core:welcome")
    return render(request, "setup/done.html")
