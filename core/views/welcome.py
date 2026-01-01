from django.shortcuts import render, redirect
from core.models.setup import SetupState

def welcome(request):
    state, _ = SetupState.objects.get_or_create(
        id=1, defaults={"is_completed": False, "current_step": 1}
    )

    if state.is_completed:
        return redirect("core:setup_done")

    if state.current_step == 1:
        return render(request, "setup/welcome.html")

    if state.current_step == 2:
        return redirect("core:setup_user")

    if state.current_step == 3:
        return redirect("core:setup_company")

    if state.current_step == 4:
        return redirect("core:setup_general")

    # ❌ JANGAN reset step di sini
    # kalau state aneh, lempar balik ke welcome TANPA ubah DB
    return render(request, "setup/welcome.html")
