from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"

    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="conversations")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.DIRECT)
    name = models.CharField(max_length=80, blank=True)
    direct_key = models.CharField(max_length=40, unique=True, null=True, blank=True)  # "minId-maxId", prevents duplicate DMs
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-last_message_at"]
        indexes = [models.Index(fields=["institution", "-last_message_at"])]


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_participations")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="uniq_conversation_participant")]
        indexes = [models.Index(fields=["user"])]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]
