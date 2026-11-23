from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.ask.models import Question
from apps.circles.models import Circle
from apps.communities.models import Community
from apps.communities.services import my_active_ids
from apps.connections.services import blocked_ids
from apps.discussions.models import Post
from apps.events.models import Event
from apps.profiles.services import candidate_queryset
from apps.projects.models import Project

User = get_user_model()


def run_search(user, q, limit=5):
    """Campus-wide search. Every section applies the same visibility rules as its own module."""
    q = (q or "").strip()
    if len(q) < 2:
        return {}
    inst, blocked, mine = user.institution_id, blocked_ids(user), my_active_ids(user)
    people = candidate_queryset(user).filter(
        Q(full_name__icontains=q) | Q(profile__bio__icontains=q) | Q(profile__study_subjects__icontains=q)
        | Q(profile__interests__name__icontains=q) | Q(profile__skills__name__icontains=q)).distinct()[:limit]
    faculty = (User.objects.filter(institution_id=inst, role="faculty", is_approved=True, is_active=True)
               .exclude(pk__in=blocked).filter(Q(full_name__icontains=q) | Q(faculty_profile__expertise__icontains=q)
               | Q(faculty_profile__research_interests__icontains=q)).select_related("faculty_profile", "profile").distinct()[:limit])
    posts = (Post.objects.filter(community__institution_id=inst, is_removed=False).filter(Q(community__visibility="public") | Q(community_id__in=mine))
             .exclude(author_id__in=blocked).filter(Q(title__icontains=q) | Q(body__icontains=q)).select_related("author", "community")[:limit])
    sections = {
        "People": list(people), "Faculty": list(faculty),
        "Communities": list(Community.objects.filter(institution_id=inst).filter(Q(name__icontains=q) | Q(description__icontains=q))[:limit]),
        "Circles": list(Circle.objects.filter(institution_id=inst, status="open").filter(Q(name__icontains=q) | Q(purpose__icontains=q))[:limit]),
        "Projects": list(Project.objects.filter(institution_id=inst).filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(technologies__icontains=q))[:limit]),
        "Events": list(Event.objects.filter(institution_id=inst).filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(venue__icontains=q)).order_by("-start_at")[:limit]),
        "Posts": list(posts),
        "Questions": list(Question.objects.filter(institution_id=inst, is_removed=False).exclude(author_id__in=blocked)
                          .filter(Q(title__icontains=q) | Q(body__icontains=q))[:limit]),
    }
    return {k: v for k, v in sections.items() if v}
