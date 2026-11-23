from django.conf import settings
from django.db import models
from django.db.models import Q

ASK_CATEGORIES = [("academics", "Academics"), ("programming", "Programming"), ("projects", "Projects"), ("career", "Career"),
                  ("internships", "Internships"), ("campus", "Campus Help"), ("general", "General Questions")]


class Question(models.Model):
    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="questions")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    category = models.CharField(max_length=15, choices=ASK_CATEGORIES, default="general")
    title = models.CharField(max_length=150)
    body = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_removed = models.BooleanField(default=False)
    accepted_answer = models.ForeignKey("Answer", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "-created_at"]), models.Index(fields=["institution", "category"])]


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    body = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_removed = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["question", "author"], name="one_answer_per_user")]


class AnswerVote(models.Model):
    """'This was helpful'. Self-votes are blocked in the view; badges also ignore them."""
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_votes")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["answer", "user"], name="uniq_answer_vote")]


class AnswerComment(models.Model):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_comments")
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class QuestionBookmark(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_bookmarks")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["question", "user"], name="uniq_question_bookmark")]


class AskReport(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        INAPPROPRIATE = "inappropriate", "Inappropriate"
        MISINFO = "misinformation", "Misinformation"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Removed"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ask_reports")
    institution = models.ForeignKey("institutions.Institution", on_delete=models.CASCADE, related_name="+")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=(Q(question__isnull=False) & Q(answer__isnull=True)) | (Q(question__isnull=True) & Q(answer__isnull=False)), name="ask_report_one_target"),
            models.UniqueConstraint(fields=["reporter", "question"], condition=Q(question__isnull=False), name="uniq_ask_report_q"),
            models.UniqueConstraint(fields=["reporter", "answer"], condition=Q(answer__isnull=False), name="uniq_ask_report_a"),
        ]
