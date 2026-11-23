from django.urls import path
from . import views

app_name = "profiles"
urlpatterns = [
    path("welcome/<int:step>/", views.onboarding, name="onboarding"),
    path("people/", views.discover, name="discover"),
    path("people/<int:pk>/", views.profile_detail, name="detail"),
    path("me/", views.my_profile, name="me"),
    path("me/edit/", views.profile_edit, name="edit"),
]
