from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import AbstractTask
from apps.core.forms import http_only

CIRCLE_CATEGORIES = [
    ("study", "Study"), ("technology", "Technology"), ("academics", "Academics"), ("gaming", "Gaming"),
    ("sports", "Sports"), ("arts", "Arts"), ("music", "Music"), ("entrepreneurship", "Entrepreneurship"), ("general", "General"),
]


class Circle(models.Model):
    class Kind(models.TextChoices):
        GENERAL = "general", "Circle"
        STUDY = "study", "Study group"

    class JoinPolicy(models.TextChoices):
        OPEN = "open", "Anyone can join"
        APPROVAL = "approval", "Owner approves requests"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="circles")
    name = models.CharField(max_length=80)
    purpose = models.CharField(max_length=400)
    category = models.CharField(max_length=20, choices=CIRCLE_CATEGORIES, default="general")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.GENERAL)
    max_members = models.PositiveSmallIntegerField(default=8, validators=[MinValueValidator(2), MaxValueValidator(50)])
    join_policy = models.CharField(max_length=10, choices=JoinPolicy.choices, default=JoinPolicy.OPEN)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_circles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "kind", "status"])]

    def __str__(self):
        return self.name


class CircleMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Requested"
        INVITED = "invited", "Invited"

    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_memberships")
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["circle", "user"], name="uniq_circle_membership")]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["circle", "status"])]


class CirclePost(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_posts")
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CircleResource(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="resources")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_resources")
    title = models.CharField(max_length=120)
    url = models.URLField(max_length=500, validators=[http_only])
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class StudySession(models.Model):
    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In person"

    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60, validators=[MinValueValidator(15), MaxValueValidator(480)])
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ONLINE)
    location = models.CharField(max_length=200, blank=True, help_text="Meeting link or place")
    notes = models.CharField(max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["circle", "starts_at"])]


class CircleTask(AbstractTask):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="tasks")
