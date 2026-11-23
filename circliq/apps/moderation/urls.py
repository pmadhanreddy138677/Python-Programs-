from django.urls import path
from . import views

app_name = "moderation"
urlpatterns = [
    path("posts/<int:pk>/report/", views.report_post, name="report_post"),
    path("comments/<int:pk>/report/", views.report_comment, name="report_comment"),
    path("communities/<int:pk>/moderation/", views.queue, name="queue"),
    path("posts/<int:pk>/remove/", views.remove_post, name="remove_post"),
    path("reports/<int:pk>/<str:action>/", views.resolve, name="resolve"),
]
