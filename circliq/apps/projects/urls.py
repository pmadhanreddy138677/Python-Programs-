from django.urls import path
from . import views as v

app_name = "projects"
urlpatterns = [
    path("", v.project_list, name="list"),
    path("new/", v.project_create, name="create"),
    path("<int:pk>/", v.project_detail, name="detail"),
    path("<int:pk>/edit/", v.project_edit, name="edit"),
    path("<int:pk>/apply/", v.project_apply, name="apply"),
    path("<int:pk>/withdraw/", v.project_withdraw, name="withdraw"),
    path("<int:pk>/leave/", v.project_leave, name="leave"),
    path("<int:pk>/status/", v.project_status, name="status"),
    path("<int:pk>/members/<int:mid>/remove/", v.member_remove, name="member_remove"),
    path("applications/<int:pk>/<str:action>/", v.application_action, name="application"),
    path("<int:pk>/tasks/new/", v.task_new, name="task_new"),
    path("tasks/<int:pk>/move/", v.task_move, name="task_move"),
    path("tasks/<int:pk>/delete/", v.task_delete, name="task_delete"),
    path("<int:pk>/comments/new/", v.comment_new, name="comment_new"),
    path("comments/<int:pk>/delete/", v.comment_delete, name="comment_delete"),
]
