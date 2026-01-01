from django.shortcuts import render, redirect
from core.models.setup import SetupState
from core.forms.general import GeneralConfigForm

def setup_general(request):
    state = SetupState.objects.get(id=1)

    if state.is_completed:
        return redirect("core:setup_done")
    if state.current_step < 4:
        return redirect("core:welcome")

    if request.method == "POST":
        form = GeneralConfigForm(request.POST)
        if form.is_valid():
            form.save()
            state.is_completed = True
            state.save(update_fields=["is_completed"])
            return redirect("core:setup_done")
    else:
        form = GeneralConfigForm()

    return render(request, "setup/general.html", {"form": form})
