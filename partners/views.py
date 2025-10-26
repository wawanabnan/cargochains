from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.shortcuts import redirect

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