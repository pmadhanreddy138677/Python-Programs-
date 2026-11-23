from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.circles.models import Circle, CircleMembership as M
from apps.circles.services import attach_state, with_counts, with_members
from .forms import StudyRequestForm
from .models import StudyRequest


@login_required
def study_list(request):
    me = request.user
    q, mode, scope = (request.GET.get("q") or "").strip(), request.GET.get("mode", ""), request.GET.get("scope", "")
    circles = with_members(with_counts(Circle.objects.filter(institution_id=me.institution_id, kind="study")))
    reqs = StudyRequest.objects.filter(circle__in=circles).select_related("circle", "circle__created_by__profile")
    if q:
        reqs = reqs.filter(Q(subject__icontains=q) | Q(topic__icontains=q) | Q(description__icontains=q))
    if mode in dict(StudyRequest.Mode.choices):
        reqs = reqs.filter(Q(mode=mode) | Q(mode="either"))
    if scope == "mine":
        reqs = reqs.filter(circle__memberships__user=me, circle__memberships__status="active")
    else:
        reqs = reqs.filter(circle__status="open")
    page = Paginator(reqs, 12).get_page(request.GET.get("page"))
    # attach annotated circle objects (member counts, avatars, state) to each request
    cmap = {c.pk: c for c in circles.filter(pk__in=[r.circle_id for r in page])}
    attach_state(me, cmap.values())
    for r in page:
        r.c = cmap[r.circle_id]
        r.slots = max(r.c.max_members - r.c.member_count, 0)
        r.dots = ["on"] * r.c.member_count + ["off"] * r.slots
    params = request.GET.copy(); params.pop("page", None)
    return render(request, "study/list.html", {"page": page, "q": q, "mode": mode, "scope": scope,
                                                "modes": StudyRequest.Mode.choices, "querystring": params.urlencode()})


@login_required
@rate_limit("study_new", 15, 3600)
def study_create(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved first.")
        return redirect("study:list")
    form = StudyRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            circle = Circle.objects.create(
                institution=me.institution, created_by=me, kind="study", category="study", join_policy="open",
                name=f"{d['subject']} · {d['topic']}"[:80], purpose=d["goal"][:400], max_members=d["group_size"])
            M.objects.create(circle=circle, user=me, role="owner", status="active")
            r = form.save(commit=False)
            r.circle = circle
            r.save()
        messages.success(request, "Study request posted. Your group workspace is ready.")
        return redirect("circles:detail", pk=circle.pk)
    return render(request, "study/form.html", {"form": form})
