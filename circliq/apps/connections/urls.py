from django.urls import path
from . import views

app_name = "connections"
urlpatterns = [
    path("", views.connection_list, name="list"),
    path("send/<int:pk>/", views.send_request, name="send"),
    path("respond/<int:pk>/<str:action>/", views.respond, name="respond"),
    path("cancel/<int:pk>/", views.cancel_or_remove, name="cancel"),
    path("block/<int:pk>/", views.block, name="block"),
    path("unblock/<int:pk>/", views.unblock, name="unblock"),
]
