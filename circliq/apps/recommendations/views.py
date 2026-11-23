from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import engine
from .search import run_search
from .services import ranked_matches


@login_required
def match(request):
    me = request.user
    if not me.profile.onboarding_complete:
        return redirect("profiles:onboarding", step=me.profile.onboarding_step)
    mode = request.GET.get("mode", "friend")
    if mode not in engine.MODES:
        mode = "friend"
    enabled = me.profile.match_enabled
    rows = ranked_matches(me, mode) if enabled else []
    p = me.profile
    missing = {"friend": not p.interests.exists(), "study": not p.study_subjects, "project": not p.skills.exists()}[mode]
    return render(request, "recommendations/match.html", {
        "modes": [(k, v) for k, v in engine.MODES.items()], "mode": mode, "info": engine.MODES[mode], "rows": rows,
        "enabled": enabled, "missing": missing})


@login_required
@require_POST
def match_toggle(request):
    p = request.user.profile
    p.match_enabled = not p.match_enabled
    p.save(update_fields=["match_enabled"])
    messages.success(request, "Campus Match is on." if p.match_enabled else "You've left Campus Match. You won't appear in matches.")
    return redirect("recommendations:match")


@login_required
@rate_limit("search", 120, 60, methods=("GET",))
def search(request):
    q = (request.GET.get("q") or "").strip()
    results = run_search(request.user, q)
    return render(request, "recommendations/search.html", {"q": q, "results": results, "total": sum(len(v) for v in results.values()), "too_short": bool(q) and len(q) < 2})
