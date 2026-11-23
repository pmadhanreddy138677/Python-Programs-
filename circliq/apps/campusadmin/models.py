from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Who did what, for every administrative action. Never contains message content."""
    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=40)
    target = models.CharField(max_length=120, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "-created_at"])]


def audit(actor, action, target="", detail=""):
    return AuditLog.objects.create(institution=actor.institution, actor=actor, action=action, target=target[:120], detail=detail[:300])
