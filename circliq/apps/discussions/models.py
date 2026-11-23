from django.conf import settings
from django.db import models


class Post(models.Model):
    class Kind(models.TextChoices):
        DISCUSSION = "discussion", "Discussion"
        QUESTION = "question", "Question"
        PROJECT = "project", "Project idea"

    community = models.ForeignKey("communities.Community", on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.DISCUSSION)
    title = models.CharField(max_length=150, blank=True)
    body = models.TextField(max_length=5000)
    image = models.ImageField(upload_to="posts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_removed = models.BooleanField(default=False)  # removed by a moderator
    accepted_comment = models.ForeignKey("Comment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["community", "-created_at"]), models.Index(fields=["kind", "-created_at"])]
        ordering = ["-created_at"]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_removed = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "created_at"])]


class Reaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="uniq_reaction")]


class Bookmark(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="uniq_bookmark")]
