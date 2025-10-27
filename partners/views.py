from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django import forms
from .models import Partner


@staff_member_required
def admin_partners_list(request):
    # ke changelist model Partner
    return redirect(reverse("admin:partners_partner_changelist"))

@staff_member_required
def admin_partners_add(request):
    # ke form tambah Partner
    return redirect(reverse("admin:partners_partner_add"))

# (opsional) kalau kamu punya filter "role" dan ingin langsung menampilkan yang Customer:
@staff_member_required
def admin_customers_only(request):
    # ganti parameter query sesuai filter yang tersedia di admin kamu
    # contoh umum: ?role__id__exact=1 atau ?role__exact=CUSTOMER
    url = reverse("admin:partners_partner_changelist") + "?role__exact=CUSTOMER"
    return redirect(url)

@staff_member_required
def partners_redirect_to_admin(request):
    return redirect(reverse("admin:partners_partner_changelist"))


def customers_list(request):
    # ambil hanya data customer
    customers = Partner.objects.filter(role="CUSTOMER").order_by("name")
    return render(request, "partners/customers_list.html", {"customers": customers})


# partners/views.py
from django.http import JsonResponse
from partners.models import Partner

def partners_autocomplete(request):
    q = (request.GET.get("q") or "").strip()
    qs = Partner.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)[:20]
    return JsonResponse([
        {"id": p.pk, "text": p.name, "address": getattr(p, "address", "")}
        for p in qs
    ], safe=False)


class PartnerMinimalForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ["name", "address", "phone", "email"]
        widgets = {
            "name": forms.TextInput(attrs={"class":"form-control", "required": True}),
            "address": forms.Textarea(attrs={"class":"form-control", "rows":2}),
            "phone": forms.TextInput(attrs={"class":"form-control"}),
            "email": forms.EmailInput(attrs={"class":"form-control"}),
        }

@login_required
@require_POST
def partner_create_minimal(request):
    form = PartnerMinimalForm(request.POST)
    if form.is_valid():
        p = form.save()
        return JsonResponse({"ok": True, "id": p.pk, "name": p.name})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)