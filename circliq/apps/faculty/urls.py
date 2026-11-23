from django.urls import path
from . import views as v

app_name = "faculty"
urlpatterns = [
    path("", v.directory, name="directory"),
    path("me/edit/", v.my_faculty_profile, name="edit"),
    path("requests/", v.requests_page, name="requests"),
    path("requests/<int:pk>/<str:action>/", v.respond_mentorship, name="respond"),
    path("announcements/", v.announcements, name="announcements"),
    path("announcements/new/", v.announcement_new, name="announcement_new"),
    path("announcements/<int:pk>/delete/", v.announcement_delete, name="announcement_delete"),
    path("<int:pk>/", v.faculty_detail, name="detail"),
    path("<int:pk>/mentorship/", v.request_mentorship, name="request"),
]
