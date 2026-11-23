from django.conf import settings
from django.db import models


class AbstractTask(models.Model):
    """Shared shape for Circle tasks and Project tasks."""

    class Status(models.TextChoices):
        TODO = "todo", "To do"
        DOING = "doing", "In progress"
        DONE = "done", "Done"

    title = models.CharField(max_length=150)
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.TODO)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]
