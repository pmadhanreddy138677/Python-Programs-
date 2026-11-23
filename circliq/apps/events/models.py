from django.conf import settings
from django.db import models

from apps.communities.models import CATEGORIES


class Event(models.Model):
    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="events")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organized_events")
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=3000)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="general")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    banner = models.ImageField(upload_to="events/", blank=True, null=True)
    is_official = models.BooleanField(default=False)  # set by the server for faculty/admin organizers
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [models.Index(fields=["institution", "start_at"])]


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_registrations")
    created_at = models.DateTimeField(auto_now_add=True)
    reminded = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="uniq_event_registration")]


class EventSave(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="saves")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_events")
    reminded = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="uniq_event_save")]
