# geo/urls.py
from django.urls import path
from .views.locations import LocationAutocompleteView  # ⬅️ arahkan ke submodule adds.py
from .views.locations import LocationAjaxView  # ⬅️ arahkan ke submodule adds.py
from .views.locations import ProvincesView, RegenciesView, DistrictsView, VillagesView,LocationChildrenView,LocationSelect2View


app_name = "geo"


urlpatterns = [
    path("locations/autocomplete/", LocationAutocompleteView.as_view(), name="locations_autocomplete"),
    path("locations/ajaxview/", LocationAjaxView.as_view(), name="locations_ajax"),
    path("provinces/", ProvincesView.as_view(), name="provinces"),
    path("regencies/", RegenciesView.as_view(), name="regencies"),
    path("districts/", DistrictsView.as_view(), name="districts"),
    path("villages/", VillagesView.as_view(), name="villages"),
    path("children/", LocationChildrenView.as_view(), name="location_children"),
    path("locations/select2/", LocationSelect2View.as_view(), name="locations_select2"),


]

