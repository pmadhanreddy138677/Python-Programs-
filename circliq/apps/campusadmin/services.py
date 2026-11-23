from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.ask.models import AskReport, Question
from apps.circles.models import Circle
from apps.communities.models import Community
from apps.discussions.models import Post
from apps.events.models import Event
from apps.moderation.models import Report
from apps.projects.models import Project

User = get_user_model()


def stats(inst):
    """Real database statistics for one campus. Deliberately contains nothing about private messages."""
    now = timezone.now()
    users = User.objects.filter(institution=inst)
    since = now - timedelta(days=13)
    per_day = dict(users.filter(date_joined__gte=since.replace(hour=0, minute=0, second=0)).annotate(d=TruncDate("date_joined")).values_list("d").annotate(n=Count("pk")))
    signups = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date()
        signups.append({"label": day.strftime("%d %b"), "n": per_day.get(day, 0)})
    top = max([s["n"] for s in signups] + [1])
    for s in signups:
        s["h"] = round(100 * s["n"] / top)
    return {
        "total_users": users.count(),
        "students": users.filter(role="student").count(), "faculty": users.filter(role="faculty", is_approved=True).count(),
        "active_7d": users.filter(last_login__gte=now - timedelta(days=7)).count(),
        "active_30d": users.filter(last_login__gte=now - timedelta(days=30)).count(),
        "new_7d": users.filter(date_joined__gte=now - timedelta(days=7)).count(),
        "unverified": users.filter(is_email_verified=False).count(),
        "restricted": users.filter(is_restricted=True).count(),
        "pending_faculty": users.filter(role="faculty", is_approved=False, is_active=True).count(),
        "communities": Community.objects.filter(institution=inst).count(),
        "official_communities": Community.objects.filter(institution=inst, is_official=True).count(),
        "active_circles": Circle.objects.filter(institution=inst, status="open").count(),
        "open_projects": Project.objects.filter(institution=inst, status="open").count(),
        "upcoming_events": Event.objects.filter(institution=inst, start_at__gte=now).count(),
        "posts": Post.objects.filter(community__institution=inst, is_removed=False).count(),
        "questions": Question.objects.filter(institution=inst, is_removed=False).count(),
        "pending_reports": Report.objects.filter(community__institution=inst, status="open").count() + AskReport.objects.filter(institution=inst, status="open").count(),
        "signups": signups,
    }
