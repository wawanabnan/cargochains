"""
URL configuration for cargochains project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# config/urls.py (atau <project_name>/urls.py)
from django.contrib import admin
from django.urls import path, include,reverse_lazy
from django.views.generic import RedirectView
from django.conf import settings          # <— INI WAJIB
from django.shortcuts import render


def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)

def custom_permission_denied(request, exception=None):
    return render(request, "403.html", status=403)

handler403 = custom_permission_denied
handler404 = custom_page_not_found


urlpatterns = [
    path("admin/", admin.site.urls),
    path("sales/", include("sales.urls", namespace="sales")),  # <— include dengan namespace
    path("account/", include("account.urls", namespace="account")),
    path("sales/config/", include("sales_configuration.urls", namespace="sales_configuration")),
    


    path("shipments/", include("shipments.urls", namespace="shipments")),  # <— include dengan namespace

    #path("", RedirectView.as_view(url=reverse_lazy(settings.LOGIN_URL), permanent=False)),
    path("partners/", include("partners.urls", namespace="partners")),  # <— include dengan namespace

    path("geo/", include(("geo.urls", "geo"), namespace="geo")),  # wajib kalau pakai {% url 'geo:...' %}
    path("projects/", include("projects.urls")),
    path("purchases/", include("purchases.urls")),

    

]

from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
