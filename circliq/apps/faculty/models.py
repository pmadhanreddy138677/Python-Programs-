from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.forms import http_only


class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faculty_profile")
    designation = models.CharField(max_length=100, blank=True)
    expertise = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. Machine Learning, Databases")
    research_interests = models.TextField(max_length=800, blank=True)
    office_hours = models.CharField(max_length=150, blank=True)
    allow_direct_messages = models.BooleanField(default=True)
    accepts_mentorship = models.BooleanField(default=True)

    def expertise_list(self):
        return [e.strip() for e in self.expertise.split(",") if e.strip()]


class MentorshipRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_requests_sent")
    faculty = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_requests_received")
    message = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["student", "faculty"], condition=Q(status="pending"), name="one_pending_mentorship_per_pair")]


class Announcement(models.Model):
    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="announcements")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=150)
    body = models.TextField(max_length=3000)
    link = models.URLField(max_length=500, blank=True, validators=[http_only])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "-created_at"])]
