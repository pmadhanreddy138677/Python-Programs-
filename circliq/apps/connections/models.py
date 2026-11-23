from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Connection(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_connections")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_connections")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requester", "receiver"], name="uniq_connection_pair"),
            models.CheckConstraint(condition=~Q(requester=F("receiver")), name="no_self_connection"),
        ]
        indexes = [models.Index(fields=["receiver", "status"]), models.Index(fields=["requester", "status"])]

    def other(self, user):
        return self.receiver if self.requester_id == user.id else self.requester


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="uniq_block_pair"),
            models.CheckConstraint(condition=~Q(blocker=F("blocked")), name="no_self_block"),
        ]
