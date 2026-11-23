from django.urls import path
from . import views as v

app_name = "messaging"
urlpatterns = [
    path("", v.inbox, name="inbox"),
    path("new-group/", v.new_group, name="new_group"),
    path("with/<int:user_id>/", v.start, name="start"),
    path("<int:pk>/", v.inbox, name="chat"),
    path("<int:pk>/send/", v.send, name="send"),
    path("<int:pk>/poll/", v.poll, name="poll"),
    path("<int:pk>/read/", v.read, name="read"),
    path("<int:pk>/leave/", v.leave, name="leave"),
]
