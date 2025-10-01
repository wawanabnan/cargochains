from django.urls import path
from ..views.actions import quick_action, assign_number

urlpatterns = [
    path("<int:pk>/quick-action/", quick_action, name="quick_action"),
    path("<int:pk>/assign-number/", assign_number, name="assign_number"),
]
