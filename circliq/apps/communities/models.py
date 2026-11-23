from django.conf import settings
from django.db import models

CATEGORIES = [
    ("technology", "Technology"), ("academics", "Academics"), ("gaming", "Gaming"), ("sports", "Sports"),
    ("arts", "Arts"), ("music", "Music"), ("entrepreneurship", "Entrepreneurship"), ("general", "General"),
]


class Community(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="communities")
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="general")
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_official = models.BooleanField(default=False)  # only settable by campus admins / Django admin
    rules = models.TextField(blank=True, max_length=1500)
    icon = models.ImageField(upload_to="communities/icons/", blank=True, null=True)
    banner = models.ImageField(upload_to="communities/banners/", blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_communities")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "communities"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["institution", "name"], name="uniq_community_name_per_institution")]
        indexes = [models.Index(fields=["institution", "category"]), models.Index(fields=["institution", "visibility"])]

    def __str__(self):
        return self.name

    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE


class CommunityMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MODERATOR = "moderator", "Moderator"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending approval"

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["community", "user"], name="uniq_membership")]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["community", "status"])]
