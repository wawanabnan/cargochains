# geo/urls.py
from django.urls import path
from .views.locations import LocationAutocompleteView  # ⬅️ arahkan ke submodule adds.py
from .views.locations import LocationAjaxView  # ⬅️ arahkan ke submodule adds.py


app_name = "geo"

urlpatterns = [
    path("locations/autocomplete/", LocationAutocompleteView.as_view(), name="locations_autocomplete"),
    path("locations/ajaxview/", LocationAjaxView.as_view(), name="locations_ajax"),
    
    
]
