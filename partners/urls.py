from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required   # ← ini yang wajib ada
from django.urls import path, reverse_lazy
from django.urls import path
from .views import partners_autocomplete, partner_create_minimal




app_name = "partnes"

urlpatterns = [
    path("autocomplete/", partners_autocomplete, name="partners_autocomplete"),
    path("create-minimal/", partner_create_minimal, name="partner_create_minimal"),    

]

