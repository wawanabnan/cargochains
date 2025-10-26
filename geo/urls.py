# geo/urls.py
from django.urls import path
from .views.adds import LocationAutocompleteView  # ⬅️ arahkan ke submodule adds.py
from .views.adds import LocationAjaxView  # ⬅️ arahkan ke submodule adds.py


app_name = "geo"

urlpatterns = [
    path("locations/autocomplete/", LocationAutocompleteView.as_view(), name="locations_autocomplete"),
    path("locations/ajaxview/", LocationAjaxView.as_view(), name="locations_ajax"),
    
    
]
