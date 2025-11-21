from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required   # ← ini yang wajib ada
from django.urls import path, reverse_lazy
from django.urls import path
#from .views import partners_autocomplete, partner_create_minimal
#from .views import PartnerQuickCreateView


from .views import (
    PartnerListView,
    PartnerCreateView,
    PartnerUpdateView,
    PartnerDeleteView,
    LocationAutocompleteView,
    PartnerAutocompleteView,
    PartnerDetailJsonView
)


app_name = "partnes"

urlpatterns = [
   # path("autocomplete/", partners_autocomplete, name="partners_autocomplete"),
   # path("create-minimal/", partner_create_minimal, name="partner_create_minimal"),    
    #path("quick-add/", PartnerQuickCreateView.as_view(), name="quick_add"),

    path("", PartnerListView.as_view(), name="partner_list"),
    path("add/", PartnerCreateView.as_view(), name="partner_add"),
    path("<int:pk>/edit/", PartnerUpdateView.as_view(), name="partner_edit"),
    path("<int:pk>/delete/", PartnerDeleteView.as_view(), name="partner_delete"),

    # autocomplete location (bisa juga diletakkan di app geo, terserah struktur om)
    path("location/autocomplete/", LocationAutocompleteView.as_view(), name="location_autocomplete"),
    path("autocomplete/", PartnerAutocompleteView.as_view(), name="partner_autocomplete"),
    path("<int:pk>/json/", PartnerDetailJsonView.as_view(), name="partner_detail_json"),



]

