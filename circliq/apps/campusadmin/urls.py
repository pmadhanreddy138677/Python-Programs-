from django.urls import path
from . import views as v

app_name = "campusadmin"
urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("users/", v.users, name="users"),
    path("users/<int:pk>/<str:action>/", v.user_action, name="user_action"),
    path("communities/", v.communities, name="communities"),
    path("communities/<int:pk>/official/", v.toggle_official, name="official"),
    path("reports/", v.reports, name="reports"),
    path("audit/", v.audit_log, name="audit"),
]
