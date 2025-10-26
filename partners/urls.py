from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required   # ← ini yang wajib ada
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView        # ← penting, ini yang belum ada
from .views_admin_bridge import (        # ← impor fungsi langsung
    customers_admin_list,
    customers_admin_add,
    customers_admin_change,
    customers_only,                       # opsional; boleh dihapus kalau tak dipakai
)


app_name = "partnes"

urlpatterns = [
    
    path("customers-admin/", customers_admin_list, name="customers_admin_list"),
    path("customers-admin/add/", customers_admin_add, name="customers_admin_add"),
    path("customers-admin/<int:object_id>/change/", customers_admin_change, name="customers_admin_change"),
    path("customers-only/", customers_only, name="customers_only"),  # opsional

    path("admin/partners/", views.admin_partners_list, name="admin_partners_list"),
    path("admin/partners/add/", views.admin_partners_add, name="admin_partners_add"),
    path("admin/customers/", views.admin_customers_only, name="admin_customers_only"),  # opsional
   # path("partners/", views.partners_redirect_to_admin, name="partners_redirect"),
   
    path(
        "",
        login_required(
            RedirectView.as_view(
                url=reverse_lazy("admin:partners_partner_changelist"),
                permanent=False,
            )
        ),
        name="redirect_to_admin",
    ),
     path("customers/", views.customers_list, name="customers_list"),


]

