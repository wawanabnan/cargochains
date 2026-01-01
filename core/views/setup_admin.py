from django.shortcuts import render, redirect
from core.models.setup import SetupState
from core.forms.admin import AdminCreateForm

def setup_user(request):
    state, _ = SetupState.objects.get_or_create(id=1)

    if state.is_completed:
        return redirect("/account/login/")
    if state.current_step >= 3:
        return redirect("core:setup_company")


    if request.method == "POST":
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            form.save()
            state.current_step = 3
            state.save(update_fields=["current_step"])
            return redirect("core:setup_company")

    else:
        form = AdminCreateForm()

    return render(request, "setup/user.html", {"form": form})
