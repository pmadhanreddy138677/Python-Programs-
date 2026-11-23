from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.circles.services import upcoming_sessions
from apps.projects.services import recommended_for
from apps.communities.services import recommend
from apps.connections.services import connection_count
from apps.discussions.feed import feed_for
from apps.discussions.forms import PostForm
from apps.events.models import Event
from apps.faculty.models import Announcement
from apps.profiles.services import suggestions
from apps.recommendations.services import nudges, picks_for

FEEDS = [("for_you", "For You"), ("mine", "My Communities"), ("latest", "Latest"), ("questions", "Questions"), ("projects", "Projects")]


def greeting_for(hour):
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@login_required
def home(request):
    from django.contrib.auth import get_user_model
    me = (get_user_model().objects.select_related("profile", "department", "institution")
          .prefetch_related("profile__interests", "profile__skills").get(pk=request.user.pk))  # reused by every service below
    if not me.profile.onboarding_complete:
        return redirect("profiles:onboarding", step=me.profile.onboarding_step)
    kind = request.GET.get("feed", "for_you")
    if kind not in dict(FEEDS):
        kind = "for_you"
    form = PostForm(user=me)
    page = Paginator(feed_for(me, kind), 8).get_page(request.GET.get("page"))
    return render(request, "dashboard/home.html", {
        "greeting": greeting_for(timezone.localtime().hour),
        "connection_count": connection_count(me),
        "completeness": me.profile.completeness(),
        "suggested": suggestions(me, 3),
        "recommended": recommend(me, 3),
        "picks": picks_for(me),
        "nudges": nudges(me),
        "sessions": upcoming_sessions(me, 3),
        "projects_rec": recommended_for(me, 2),
        "events": Event.objects.filter(institution_id=me.institution_id, start_at__gte=timezone.now()).order_by("start_at")[:3],
        "announcements": Announcement.objects.filter(institution_id=me.institution_id).select_related("author")[:2],
        "feeds": FEEDS, "feed": kind, "page": page, "form": form,
        "has_communities": form.fields["community"].queryset.exists(),
    })
