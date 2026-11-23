from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.connections.models import Connection
from apps.connections.services import blocked_ids, connection_count, relation, relations_for
from apps.institutions.models import Department
from .forms import ProfileEditForm, StepGoalsForm, StepInterestsForm, StepProfileForm
from .matching import compare
from .models import Interest, Skill
from .services import apply_filters, candidate_queryset, ranked, suggestions

User = get_user_model()
STEP_FORMS = {1: StepProfileForm, 2: StepInterestsForm, 3: StepGoalsForm}
STEP_TITLES = {1: "Complete your profile", 2: "Pick your interests and skills",
               3: "What are you looking for?", 4: "Discover your first circle", 5: "Welcome to circliq"}


@login_required
def onboarding(request, step):
    from apps.communities.models import Community
    from apps.communities.services import join, recommend
    me = request.user
    profile = me.profile
    if profile.onboarding_complete:
        return redirect("dashboard:home")
    if step < 1 or step > 5 or step > profile.onboarding_step:
        return redirect("profiles:onboarding", step=min(max(profile.onboarding_step, 1), 5))
    form = None
    if step in STEP_FORMS:
        form = STEP_FORMS[step](request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST":
        if step == 4 and "join" in request.POST:  # join a recommended community without leaving the step
            c = Community.objects.filter(pk=request.POST["join"], institution_id=me.institution_id, visibility="public").first()
            if c:
                join(me, c)
            return redirect("profiles:onboarding", step=4)
        if step == 5:
            profile.onboarding_complete = True
            profile.save(update_fields=["onboarding_complete"])
            return redirect("dashboard:home")
        if "skip" in request.POST or form is None or form.is_valid():
            if form is not None and "skip" not in request.POST:
                form.save()
            profile.onboarding_step = max(profile.onboarding_step, step + 1)
            profile.save(update_fields=["onboarding_step"])
            return redirect("profiles:onboarding", step=step + 1)
    ctx = {"step": step, "form": form, "title": STEP_TITLES[step], "steps": range(1, 6)}
    if step == 4:
        ctx["communities"] = recommend(me, 6)
    if step == 5:
        ctx["suggested"] = suggestions(me, 3)
    return render(request, "profiles/onboarding.html", ctx)


@login_required
def discover(request):
    me = request.user
    if not me.profile.onboarding_complete:
        return redirect("profiles:onboarding", step=me.profile.onboarding_step)
    qs = apply_filters(candidate_queryset(me), request.GET)
    rows = ranked(me, qs)
    page = Paginator(rows, 12).get_page(request.GET.get("page"))
    rel = relations_for(me, [r["user"].id for r in page])
    for r in page:
        r["rel"], r["conn"] = rel.get(r["user"].id, ("none", None))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "profiles/discover.html", {
        "page": page, "total": len(rows), "querystring": params.urlencode(),
        "departments": Department.objects.filter(institution_id=me.institution_id),
        "interests": Interest.objects.all(), "skills": Skill.objects.all(), "f": request.GET,
    })


@login_required
def profile_detail(request, pk):
    me = request.user
    other = get_object_or_404(User.objects.select_related("profile", "department", "program"),
                              pk=pk, institution_id=me.institution_id, is_active=True)
    if other.id in blocked_ids(me):
        raise Http404
    state, conn = relation(me, other)
    # Hidden-from-discovery profiles are visible only to the owner and existing connections.
    if state not in ("self", "connected") and not other.profile.is_discoverable:
        raise Http404
    why = compare(me, other)[1] if state != "self" else ""
    from apps.circles.models import Circle
    from apps.communities.models import Community
    from apps.projects.models import Project
    from apps.messaging.services import can_message
    from apps.ask.badges import badges_for
    own = state == "self"
    comm_qs = Community.objects.filter(memberships__user=other, memberships__status="active", institution_id=me.institution_id)
    circ_qs = Circle.objects.filter(memberships__user=other, memberships__status="active", institution_id=me.institution_id)
    if not own:  # visitors only see public communities and open circles
        comm_qs, circ_qs = comm_qs.filter(visibility="public"), circ_qs.filter(join_policy="open")
    return render(request, "profiles/detail.html", {
        "can_dm": (not own) and can_message(me, other), "badges": badges_for(other),
        "p_communities": comm_qs.distinct()[:8], "p_circles": circ_qs.distinct()[:8],
        "p_projects": Project.objects.filter(memberships__user=other, institution_id=me.institution_id).distinct()[:8],
        "p": other, "profile": other.profile, "state": state, "conn": conn, "why": why,
        "connection_count": connection_count(other),
    })


@login_required
def my_profile(request):
    return redirect("profiles:detail", pk=request.user.pk)


@login_required
def profile_edit(request):
    form = ProfileEditForm(request.POST or None, request.FILES or None, instance=request.user.profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profiles:detail", pk=request.user.pk)
    return render(request, "profiles/edit.html", {"form": form})
