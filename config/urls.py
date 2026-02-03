from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.shortcuts import render, redirect
from django.conf.urls.static import static



def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)


def custom_permission_denied(request, exception=None):
    return render(request, "403.html", status=403)


handler403 = custom_permission_denied
handler404 = custom_page_not_found

def root(request):
    return redirect("/welcome/")

urlpatterns = [
    path("", root, name="root"),

    path("admin/", admin.site.urls),

    # core (welcome + setup wizard)
    path("", include(("core.urls", "core"), namespace="core")),
    path("", include(("shipments.urls", "shipments"), namespace="shipments")),



    # account (login/logout/dashboard)
    path("account/", include("account.urls", namespace="account")),

    # modules
    path("sales/", include("sales.urls", namespace="sales")),
    path("sales/configurations/", include("sales_configuration.urls", namespace="sales_configuration")),
    path("partners/", include("partners.urls", namespace="partners")),
    path("geo/", include(("geo.urls", "geo"), namespace="geo")),
    path("projects/", include("projects.urls")),
    path("purchases/", include("purchases.urls")),

    #path("payments/", include("payments.urls", namespace="payments")),
    path("", include(("payments.urls", "payments"), namespace="payments")),

    
    path("accounting/", include("accounting.urls",namespace="accounting")),
    
    path("", include(("job.urls", "job"), namespace="job")),

    #path("job/", include("job.urls", namespace="job")),
      path(
        "job/reports/",
        include(("job.reports.urls", "job_reports"), namespace="job_reports"),
    ),
    path(
        "sales/reports/",
        include(("sales.reports.urls", "sales_reports"), namespace="sales_reports"),
    ),

   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
