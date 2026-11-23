from django.db import models


class StudyRequest(models.Model):
    """A listing for a study group. Each request owns a Circle (kind=study) that holds the workspace."""

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In person"
        EITHER = "either", "Online or in person"

    circle = models.OneToOneField("circles.Circle", on_delete=models.CASCADE, related_name="study_request")
    subject = models.CharField(max_length=80)
    topic = models.CharField(max_length=120)
    description = models.CharField(max_length=600, blank=True)
    goal = models.CharField(max_length=200)
    schedule = models.CharField(max_length=120, help_text="e.g. Weekday evenings, Sat mornings")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.EITHER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
