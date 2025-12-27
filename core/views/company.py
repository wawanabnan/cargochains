from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.urls import reverse

from core.forms.company import CompanyProfileForm
from core.models.company import CompanyProfile


def is_admin(user):
    # om bisa ganti rule ini: group "Admin" atau superuser
    return user.is_superuser or user.groups.filter(name="Admin").exists()


@login_required
@user_passes_test(is_admin)
def company_settings(request):
    company = CompanyProfile.objects.first()

    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            obj = form.save(commit=False)

            # Guard single record:
            # kalau belum ada record, create; kalau sudah ada, update instance itu saja
            obj.pk = company.pk if company else obj.pk
            obj.save()
            form.save_m2m()

            return redirect(reverse("core:company_settings"))
    else:
        form = CompanyProfileForm(instance=company)

    ctx = {
        "form": form,
        "company": company,
        "page_title": "Company Information",
        "is_setup": company is None,
    }
    return render(request, "core/company_settings.html", ctx)
