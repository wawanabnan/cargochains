from django.contrib import admin
from django.urls import path, include,reverse_lazy
from django.views.generic import RedirectView
from django.conf import settings          # <— INI WAJIB
from django.shortcuts import render

from account.views import DashboardView

def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)

def custom_permission_denied(request, exception=None):
    return render(request, "403.html", status=403)

handler403 = custom_permission_denied
handler404 = custom_page_not_found


urlpatterns = [

    path("", DashboardView.as_view(), name="dashboard"),
    path("admin/", admin.site.urls),
    path("sales/", include("sales.urls", namespace="sales")),  # <— include dengan namespace
    path("account/", include("account.urls", namespace="account")),
    path("sales/config/", include("sales_configuration.urls", namespace="sales_configuration")),
    
    #path("", RedirectView.as_view(url=reverse_lazy(settings.LOGIN_URL), permanent=False)),
    path("partners/", include("partners.urls", namespace="partners")),  # <— include dengan namespace
    path("geo/", include(("geo.urls", "geo"), namespace="geo")),  # wajib kalau pakai {% url 'geo:...' %}
    path("projects/", include("projects.urls")),
    path("purchases/", include("purchases.urls")),

    

]

from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
