from django.conf import settings
from django.db import models

GOAL_CHOICES = [
    ("friends", "Make New Friends"), ("study", "Find Study Partners"), ("communities", "Join Communities"),
    ("projects", "Find Project Teammates"), ("skills", "Learn New Skills"), ("campus", "Explore Campus Activities"),
]
GOAL_PHRASES = {
    "friends": "new friends", "study": "study partners", "communities": "communities to join",
    "projects": "project teammates", "skills": "new skills to learn", "campus": "campus activities",
}


AVAILABILITY = [
    ("wd_morning", "Weekday mornings"), ("wd_afternoon", "Weekday afternoons"), ("wd_evening", "Weekday evenings"),
    ("we_morning", "Weekend mornings"), ("we_afternoon", "Weekend afternoons"), ("we_evening", "Weekend evenings"),
]
COLLAB_PREFS = [
    ("online", "Online"), ("in_person", "In person"), ("small_groups", "Small groups"), ("long_term", "Long-term projects"),
    ("hackathons", "Hackathons"), ("study_sessions", "Regular study sessions"),
]


class Interest(models.Model):
    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    bio = models.CharField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    interests = models.ManyToManyField(Interest, blank=True, related_name="profiles")
    skills = models.ManyToManyField(Skill, blank=True, related_name="profiles")
    goals = models.JSONField(default=list, blank=True)
    is_discoverable = models.BooleanField(default=True, help_text="Let other students find you in Discover.")
    # Campus Match inputs. All optional and supplied by the student; nothing is inferred.
    study_subjects = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. DBMS, Python, Statistics")
    availability = models.JSONField(default=list, blank=True)
    collab_preferences = models.JSONField(default=list, blank=True)
    match_enabled = models.BooleanField(default=True, help_text="Take part in Campus Match (see and be suggested to others).")
    onboarding_step = models.PositiveSmallIntegerField(default=1)
    onboarding_complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user}"

    def completeness(self):
        checks = [bool(self.avatar), bool(self.bio), bool(self.interests.all()), bool(self.skills.all()), bool(self.goals),
                  bool(self.study_subjects), bool(self.availability)]
        return int(sum(checks) / len(checks) * 100)

    def subject_list(self):
        return [s.strip() for s in self.study_subjects.split(",") if s.strip()]

    def availability_labels(self):
        d = dict(AVAILABILITY)
        return [d[a] for a in self.availability if a in d]

    def collab_labels(self):
        d = dict(COLLAB_PREFS)
        return [d[c] for c in self.collab_preferences if c in d]

    def goal_labels(self):
        d = dict(GOAL_CHOICES)
        return [d[g] for g in self.goals if g in d]
