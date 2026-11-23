from django.conf import settings
from django.db import models
from django.db.models import Q


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harassment or bullying"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        MISINFO = "misinformation", "Misinformation"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Content removed"
        DISMISSED = "dismissed", "Dismissed"

    community = models.ForeignKey("communities.Community", on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    post = models.ForeignKey("discussions.Post", on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    comment = models.ForeignKey("discussions.Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=(Q(post__isnull=False) & Q(comment__isnull=True)) | (Q(post__isnull=True) & Q(comment__isnull=False)),
                                   name="report_has_exactly_one_target"),
            models.UniqueConstraint(fields=["reporter", "post"], condition=Q(post__isnull=False), name="uniq_report_post"),
            models.UniqueConstraint(fields=["reporter", "comment"], condition=Q(comment__isnull=False), name="uniq_report_comment"),
        ]
        indexes = [models.Index(fields=["community", "status"])]


class ModerationAction(models.Model):
    """Audit log of every moderator/admin action."""
    community = models.ForeignKey("communities.Community", on_delete=models.CASCADE, related_name="moderation_actions")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="moderation_actions")
    action = models.CharField(max_length=30)
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
