from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import AbstractTask

PROJECT_CATEGORIES = [("web", "Web"), ("mobile", "Mobile"), ("ai_ml", "AI / ML"), ("game", "Games"),
                      ("hardware", "Hardware / IoT"), ("research", "Research"), ("design", "Design"), ("other", "Other")]


class Project(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Recruiting"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CLOSED = "closed", "Closed"

    class Kind(models.TextChoices):
        PROJECT = "project", "Student project"
        MENTORSHIP = "mentorship", "Mentorship"
        RESEARCH = "research", "Research opportunity"

    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="projects")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_projects")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=2000)
    category = models.CharField(max_length=12, choices=PROJECT_CATEGORIES, default="web")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PROJECT)
    required_skills = models.ManyToManyField("profiles.Skill", blank=True, related_name="projects")
    technologies = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. Django, React")
    team_size = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(2), MaxValueValidator(20)])
    deadline = models.DateField(null=True, blank=True)
    goals = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "status", "-created_at"])]

    def __str__(self):
        return self.title

    def tech_list(self):
        return [t.strip() for t in self.technologies.split(",") if t.strip()]


class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        MEMBER = "member", "Member"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="uniq_project_member")]
        indexes = [models.Index(fields=["user"])]


class ProjectApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Not selected"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_applications")
    message = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["project", "applicant"], name="uniq_project_application")]


class ProjectTask(AbstractTask):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")


class ProjectComment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_comments")
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
