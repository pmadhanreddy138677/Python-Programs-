from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        CONNECTION_REQUEST = "connection_request", "Connection request"
        CONNECTION_ACCEPTED = "connection_accepted", "Connection accepted"
        COMMUNITY = "community", "Community"
        CIRCLE = "circle", "Circle"
        PROJECT = "project", "Project"
        MESSAGE = "message", "Message"
        REPLY = "reply", "Reply"
        EVENT = "event", "Event"
        ANNOUNCEMENT = "announcement", "Announcement"
        MENTORSHIP = "mentorship", "Mentorship"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=300, blank=True)
    url = models.CharField(max_length=300, blank=True)
    ref = models.CharField(max_length=60, blank=True)  # used to coalesce e.g. many messages in one chat
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]
