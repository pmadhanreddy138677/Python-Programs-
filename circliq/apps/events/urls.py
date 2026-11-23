from django.urls import path
from . import views as v

app_name = "events"
urlpatterns = [
    path("", v.event_list, name="list"),
    path("new/", v.event_create, name="create"),
    path("<int:pk>/", v.event_detail, name="detail"),
    path("<int:pk>/edit/", v.event_edit, name="edit"),
    path("<int:pk>/delete/", v.event_delete, name="delete"),
    path("<int:pk>/register/", v.event_register, name="register"),
    path("<int:pk>/unregister/", v.event_unregister, name="unregister"),
    path("<int:pk>/save/", v.event_save, name="save"),
]
