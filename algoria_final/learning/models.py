from django.conf import settings
from django.db import models


# --------------------------------------------------------------------- core --
class Profile(models.Model):
    """Everything about a student (or teacher) beyond login credentials:
    XP, level, streak, current topic/path, and accessibility preferences."""

    ROLE_CHOICES = [("student", "Student"), ("teacher", "Teacher")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")
    display_name = models.CharField(max_length=80, blank=True)

    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)

    streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    streak_freeze_charges = models.PositiveIntegerField(default=1)
    freeze_refill_week = models.DateField(null=True, blank=True)

    current_topic = models.CharField(max_length=120, default="Python Syntax")
    assessment_taken = models.BooleanField(default=False)
    recommended_topic_slug = models.CharField(max_length=120, blank=True)

    # Accessibility / customization (feature 12)
    theme_mode = models.CharField(max_length=10, default="dark")       # dark / light
    font_size = models.CharField(max_length=10, default="medium")      # medium / large
    reduce_motion = models.BooleanField(default=False)
    density = models.CharField(max_length=12, default="comfortable")   # comfortable / compact

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def name(self):
        return self.display_name or self.user.first_name or self.user.username

    @property
    def is_teacher(self):
        return self.role == "teacher"


class Badge(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=10, default="🏆")
    description = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="earned_badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")

    def __str__(self):
        return f"{self.user} — {self.badge}"


class GameCompletion(models.Model):
    """One row per finished (legacy) 5-task Game Mode run."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="game_completions")
    topic = models.CharField(max_length=120, default="Python Basics")
    score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField()
    xp_awarded = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    @property
    def is_perfect(self):
        return self.score >= self.max_score

    def __str__(self):
        return f"{self.user} — {self.score}/{self.max_score}"


# ------------------------------------------------------------- learning path --
class Topic(models.Model):
    """A learning topic, grouped into the three requested topic areas."""

    GROUP_CHOICES = [
        ("foundations", "Python syntax, variables, operators, data types & I/O"),
        ("control_flow", "Conditions, loops, functions & modular design"),
        ("data_structures", "Lists, tuples, sets, dictionaries, strings & data handling"),
        ("file_handling", "Reading/writing files & exception handling"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES)
    order = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=10, default="📘")

    class Meta:
        ordering = ["group", "order"]

    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY_CHOICES = [("easy", "🟢 Easy"), ("medium", "🟡 Medium"), ("hard", "🔴 Hard")]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="easy")
    text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_option = models.PositiveSmallIntegerField()  # 1-4
    explanation = models.TextField()

    def options(self):
        return [self.option1, self.option2, self.option3, self.option4]

    def is_correct(self, chosen_option):
        try:
            return int(chosen_option) == self.correct_option
        except (TypeError, ValueError):
            return False

    def __str__(self):
        return f"[{self.topic.slug}] {self.text[:50]}"


class QuizAttempt(models.Model):
    """One finished round of the generic quiz engine — topic practice, daily
    challenge, placement assessment, smart revision, or a friend challenge."""

    SOURCE_CHOICES = [
        ("practice", "Topic practice"), ("daily", "Daily challenge"),
        ("assessment", "Placement assessment"), ("revision", "Smart revision"),
        ("friend_challenge", "Friend challenge"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="quiz_attempts")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="practice")
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    xp_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.source} {self.score}/{self.total}"


class QuestionAttempt(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    chosen_option = models.PositiveSmallIntegerField(null=True, blank=True)
    correct = models.BooleanField(default=False)


class RevisionItem(models.Model):
    """A question a student got wrong, queued for Smart Revision Mode."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="revision_items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    times_missed = models.PositiveIntegerField(default=1)
    mastered = models.BooleanField(default=False)
    next_review_date = models.DateField()
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")


# --------------------------------------------------------------- daily challenge --
class DailyChallengeLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="daily_logs")
    date = models.DateField()
    completed = models.BooleanField(default=False)
    xp_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date")


# --------------------------------------------------------------------- projects --
class Project(models.Model):
    """A 'Build Something Real' guided mini-project."""
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    brief = models.TextField()
    starter_code = models.TextField(blank=True)
    checklist = models.TextField(help_text="One requirement per line.")
    xp_reward = models.PositiveIntegerField(default=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def checklist_items(self):
        return [line for line in self.checklist.splitlines() if line.strip()]

    def __str__(self):
        return self.title


class ProjectSubmission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="project_submissions")
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    code = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "project")


# ---------------------------------------------------------------- teacher tools --
class Assignment(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="assignments_created")
    title = models.CharField(max_length=150)
    instructions = models.TextField(blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AssignmentCompletion(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE,
                                    related_name="completions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("assignment", "user")


# ------------------------------------------------------------------- friends --
class Friendship(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("accepted", "Accepted")]

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="friend_requests_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="friend_requests_received")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")


class FriendChallenge(models.Model):
    STATUS_CHOICES = [("pending", "Waiting"), ("completed", "Completed")]

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="challenges_sent")
    opponent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="challenges_received")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    creator_attempt = models.ForeignKey(QuizAttempt, on_delete=models.SET_NULL, null=True,
                                         blank=True, related_name="+")
    opponent_attempt = models.ForeignKey(QuizAttempt, on_delete=models.SET_NULL, null=True,
                                          blank=True, related_name="+")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def winner(self):
        """Returns the winning User, the string 'tie', or None if either
        side hasn't played yet."""
        if not self.creator_attempt or not self.opponent_attempt:
            return None
        if self.creator_attempt.score > self.opponent_attempt.score:
            return self.created_by
        if self.opponent_attempt.score > self.creator_attempt.score:
            return self.opponent
        return "tie"
