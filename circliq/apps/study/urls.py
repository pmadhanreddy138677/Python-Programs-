from django.urls import path
from . import views

app_name = "study"
urlpatterns = [path("", views.study_list, name="list"), path("new/", views.study_create, name="create")]
