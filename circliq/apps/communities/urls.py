from django.urls import path
from . import views

app_name = "communities"
urlpatterns = [
    path("", views.community_list, name="list"),
    path("new/", views.community_create, name="create"),
    path("<int:pk>/", views.community_detail, name="detail"),
    path("<int:pk>/edit/", views.community_edit, name="edit"),
    path("<int:pk>/join/", views.community_join, name="join"),
    path("<int:pk>/leave/", views.community_leave, name="leave"),
    path("<int:pk>/official/", views.toggle_official, name="official"),
    path("<int:pk>/members/<int:mid>/<str:action>/", views.member_action, name="member_action"),
]
