from django.urls import path, include

app_name = "shipments"

urlpatterns = [
    path("", include("shipments.urls.list")),
    path("", include("shipments.urls.detail")),
    path("", include("shipments.urls.logs")),
    path("", include("shipments.urls.actions")),  # <-- butuh file actions.py
]
