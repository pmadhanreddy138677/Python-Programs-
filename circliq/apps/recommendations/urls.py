from django.urls import path
from . import views

app_name = "recommendations"
urlpatterns = [
    path("match/", views.match, name="match"),
    path("match/toggle/", views.match_toggle, name="match_toggle"),
    path("search/", views.search, name="search"),
]
