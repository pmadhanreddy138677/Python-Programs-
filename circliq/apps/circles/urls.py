from django.urls import path
from . import views as v

app_name = "circles"
urlpatterns = [
    path("", v.circle_list, name="list"),
    path("new/", v.circle_create, name="create"),
    path("<int:pk>/", v.circle_detail, name="detail"),
    path("<int:pk>/edit/", v.circle_edit, name="edit"),
    path("<int:pk>/join/", v.circle_join, name="join"),
    path("<int:pk>/leave/", v.circle_leave, name="leave"),
    path("<int:pk>/disband/", v.circle_disband, name="disband"),
    path("<int:pk>/toggle/", v.circle_toggle, name="toggle"),
    path("<int:pk>/invite/", v.invite, name="invite"),
    path("<int:pk>/invite/<str:action>/", v.respond_invite, name="respond_invite"),
    path("<int:pk>/members/<int:mid>/<str:action>/", v.member_action, name="member_action"),
    path("<int:pk>/posts/new/", v.post_new, name="post_new"),
    path("posts/<int:pk>/delete/", v.post_delete, name="post_delete"),
    path("<int:pk>/resources/new/", v.resource_new, name="resource_new"),
    path("resources/<int:pk>/delete/", v.resource_delete, name="resource_delete"),
    path("<int:pk>/sessions/new/", v.session_new, name="session_new"),
    path("sessions/<int:pk>/delete/", v.session_delete, name="session_delete"),
    path("<int:pk>/tasks/new/", v.task_new, name="task_new"),
    path("tasks/<int:pk>/move/", v.task_move, name="task_move"),
    path("tasks/<int:pk>/delete/", v.task_delete, name="task_delete"),
]
