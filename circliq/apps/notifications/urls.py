from django.urls import path
from . import views

app_name = "notifications"
urlpatterns = [
    path("", views.notification_list, name="list"),
    path("preview/", views.preview, name="preview"),
    path("count/", views.count, name="count"),
    path("open/<int:pk>/", views.open_notification, name="open"),
    path("read-all/", views.mark_all, name="mark_all"),
]
