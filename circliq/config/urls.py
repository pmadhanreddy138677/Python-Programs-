from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.static import serve
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.core import views as core_views

handler403 = "apps.accounts.views.error_403"
handler404 = "apps.accounts.views.error_404"
handler500 = "apps.accounts.views.error_500"

urlpatterns = [
    path("", TemplateView.as_view(template_name="landing/home.html"), name="landing"),
    path("accounts/", include("apps.accounts.urls")),
    path("app/connections/", include("apps.connections.urls")),
    path("app/notifications/", include("apps.notifications.urls")),
    path("app/messages/", include("apps.messaging.urls")),
    path("app/faculty/", include("apps.faculty.urls")),
    path("app/events/", include("apps.events.urls")),
    path("app/", include("apps.recommendations.urls")),
    path("app/ask/", include("apps.ask.urls")),
    path("app/admin/", include("apps.campusadmin.urls")),
    path("app/circles/", include("apps.circles.urls")),
    path("app/study/", include("apps.study.urls")),
    path("app/projects/", include("apps.projects.urls")),
    path("app/communities/", include("apps.communities.urls")),
    path("app/", include("apps.discussions.urls")),
    path("app/", include("apps.moderation.urls")),
    path("app/", include("apps.profiles.urls")),
    path("app/", include("apps.dashboard.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
    path("healthz/", core_views.healthz, name="healthz"),
    # Uploaded files require a signed-in user. For production at scale, serve /media/ from the web server or object storage.
    re_path(r"^media/(?P<path>.*)$", login_required(serve), {"document_root": settings.MEDIA_ROOT}),
]
