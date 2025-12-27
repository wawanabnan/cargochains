from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.services.setup import get_setup_state
from core.models.company import CompanyProfile
from core.forms.company import CompanyProfileForm


def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


SETUP_MAX_STEP = 3


@login_required
@user_passes_test(is_admin)
def setup_step(request, step: int):
    state = get_setup_state()

    # normalize step
    step = int(step)
    if step < 1:
        step = 1
    if step > SETUP_MAX_STEP:
        step = SETUP_MAX_STEP

    # kalau sudah completed, wizard tidak boleh diakses
    if state.is_completed:
        return redirect(reverse("core:company_settings"))

    # STEP 1: Company Profile (mandatory)
    if step == 1:
        company = CompanyProfile.objects.first()
        from geo.models import Location

        indo = Location.objects.filter(kind="country", name__iexact="Indonesia", status="active").first()
        if indo:
            obj.country = indo

        if request.method == "POST":
            form = CompanyProfileForm(request.POST, request.FILES, instance=company)

            if form.is_valid():
                obj = form.save(commit=False)

                # guard single record
                if company:
                    obj.pk = company.pk

                # Country Indonesia bisa auto-set kalau field disabled/blank
                # (optional - sesuaikan strategi om)
                obj.save()

                # next step
                state.current_step = 2
                state.save(update_fields=["current_step", "updated_at"])
                return redirect(reverse("core:setup_step", kwargs={"step": 2}))
        else:
            form = CompanyProfileForm(instance=company)

        return render(
            request,
            "setup/step_company.html",
            {
                "step": 1,
                "max_step": SETUP_MAX_STEP,
                "title": "Initial Setup — Company Profile",
                "form": form,
                "can_skip": False,
            },
        )

    # STEP 2: Core Settings (optional) — placeholder dulu
    if step == 2:
        if request.method == "POST":
            action = request.POST.get("action")
            if action == "skip":
                state.current_step = 3
                state.save(update_fields=["current_step", "updated_at"])
                return redirect(reverse("core:setup_step", kwargs={"step": 3}))

            # nanti di sini kita simpan core settings (tax, payment terms, dll)
            # untuk sekarang anggap "save" = next
            state.current_step = 3
            state.save(update_fields=["current_step", "updated_at"])
            return redirect(reverse("core:setup_step", kwargs={"step": 3}))

        return render(
            request,
            "setup/step_core_settings.html",
            {
                "step": 2,
                "max_step": SETUP_MAX_STEP,
                "title": "Initial Setup — Core Settings",
                "can_skip": True,
            },
        )

    # STEP 3: Sales Settings (optional) — placeholder dulu
    if step == 3:
        if request.method == "POST":
            action = request.POST.get("action")
            if action == "skip":
                # selesai
                state.is_completed = True
                state.completed_at = timezone.now()
                state.save(update_fields=["is_completed", "completed_at", "updated_at"])
                return redirect(reverse("core:setup_done"))

            # nanti simpan number sequence, dsb
            state.is_completed = True
            state.completed_at = timezone.now()
            state.save(update_fields=["is_completed", "completed_at", "updated_at"])
            return redirect(reverse("core:setup_done"))

        return render(
            request,
            "setup/step_sales_settings.html",
            {
                "step": 3,
                "max_step": SETUP_MAX_STEP,
                "title": "Initial Setup — Sales Settings",
                "can_skip": True,
            },
        )


@login_required
@user_passes_test(is_admin)
def setup_done(request):
    return render(request, "setup/done.html", {})
