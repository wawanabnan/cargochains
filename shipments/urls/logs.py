
from django.urls import path
from ..views.logs import add_status_log
urlpatterns = [ path("<int:pk>/add-log/", add_status_log, name="add_log") ]
