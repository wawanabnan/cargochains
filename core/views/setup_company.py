from django.shortcuts import render, redirect
from core.models.setup import SetupState
from core.models.company import CompanyProfile
from core.forms.company import CompanyProfileForm


REQUIRED_FIELDS = [
    "name", "brand", "phone", "email", "website",
    "address_1", "address_2",
    "country", "province", "regency", "district",
    "postal_code",
]

def _is_blank(v):
    return v is None or str(v).strip() == ""


def setup_company(request):
    state, _ = SetupState.objects.get_or_create(id=1)

    if state.is_completed:
        return redirect("core:setup_done")
    if state.current_step < 3:
        return redirect("core:welcome")
    if state.current_step >= 4:
        return redirect("core:setup_general")

    company = CompanyProfile.objects.first()

    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)

        # tetap pakai is_valid supaya email/url validation jalan
        if form.is_valid():
            obj = form.save(commit=False)

            missing = [f for f in REQUIRED_FIELDS if _is_blank(getattr(obj, f, None))]
            if missing:
                for f in missing:
                    form.add_error(f, "Wajib diisi untuk melanjutkan setup.")
            else:
                obj.save()
                state.current_step = 4
                state.save(update_fields=["current_step"])
                return redirect("core:setup_general")
        # kalau invalid: jatuh ke render lagi (errors tampil)
    else:
        form = CompanyProfileForm(instance=company)

    return render(request, "setup/company.html", {"form": form})
