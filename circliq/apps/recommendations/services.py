from django.db.models import Q
from django.utils import timezone

from apps.circles.models import Circle
from apps.circles.services import with_counts as circle_counts
from apps.communities.services import INTEREST_CATEGORY, recommend as recommend_communities
from apps.connections.services import relations_for
from apps.events.models import Event
from apps.profiles.services import candidate_queryset
from apps.projects.services import recommended_for as recommended_projects
from . import engine


def match_candidates(me):
    return candidate_queryset(me).filter(profile__match_enabled=True)


def ranked_matches(me, mode, limit=24, candidate_limit=500):
    if mode not in engine.SCORERS or not me.profile.match_enabled:
        return []
    cats = engine.category_map()
    mine = engine.features_of(me, cats)
    scorer, rows = engine.SCORERS[mode], []
    for u in match_candidates(me)[:candidate_limit]:
        res = scorer(mine, engine.features_of(u, cats))
        if res.score > 0:
            pct = engine.strength(mode, res.score)
            rows.append({"user": u, "score": res.score, "pct": pct, "label": engine.label(pct), "reasons": res.reasons})
    rows.sort(key=lambda r: (-r["score"], r["user"].full_name.lower()))
    rows = rows[:limit]
    rel = relations_for(me, [r["user"].id for r in rows])
    for r in rows:
        r["rel"], r["conn"] = rel.get(r["user"].id, ("none", None))
    return rows


def best_per_mode(me, candidate_limit=150):
    """Top match for each mode from ONE pass over the candidates (used by the dashboard).
    Ties break exactly like ranked_matches: higher score first, then name."""
    if not me.profile.match_enabled:
        return {}
    cats = engine.category_map()
    mine = engine.features_of(me, cats)
    best = {}
    for u in match_candidates(me)[:candidate_limit]:
        f = engine.features_of(u, cats)
        for mode, scorer in engine.SCORERS.items():
            res = scorer(mine, f)
            if res.score <= 0:
                continue
            key = (-res.score, u.full_name.lower())
            if mode not in best or key < best[mode][0]:
                best[mode] = (key, u, res)
    return {m: {"user": u, "reasons": res.reasons} for m, (_, u, res) in best.items()}


def _interest_terms(user):
    p = user.profile
    return [i.name.lower() for i in p.interests.all()] + [s.lower() for s in p.subject_list()]


def circle_picks(user, n=2):
    from apps.circles.models import CircleMembership as CM
    terms = _interest_terms(user)
    if not terms:
        return []
    joined = set(CM.objects.filter(user=user).values_list("circle_id", flat=True))
    out = []
    for c in circle_counts(Circle.objects.filter(institution_id=user.institution_id, status="open")).exclude(pk__in=joined)[:100]:
        if c.member_count >= c.max_members:
            continue
        text = f"{c.name} {c.purpose}".lower()
        hits = [t for t in terms if t in text]
        if hits:
            out.append((len(hits), c, hits[0]))
    out.sort(key=lambda t: -t[0])
    return [(c, hit) for _, c, hit in out[:n]]


def event_picks(user, n=2):
    cats = {INTEREST_CATEGORY[i.name] for i in user.profile.interests.all() if i.name in INTEREST_CATEGORY}
    if not cats:
        return []
    qs = Event.objects.filter(institution_id=user.institution_id, start_at__gte=timezone.now(), category__in=cats).order_by("start_at")[:n]
    return list(qs)


def picks_for(user):
    """Mixed 'For you' list for the dashboard: each pick has a reason, an icon and a link."""
    picks = []
    for c in recommend_communities(user, 2):
        picks.append({"kind": "Community", "title": c.name, "reason": c.reason, "url": f"/app/communities/{c.pk}/", "icon": "grid", "tile": "t-violet"})
    for p in recommended_projects(user, 2):
        picks.append({"kind": "Project", "title": p.title, "reason": p.match_text, "url": f"/app/projects/{p.pk}/", "icon": "rocket", "tile": "t-amber"})
    for c, hit in circle_picks(user, 1):
        picks.append({"kind": "Circle", "title": c.name, "reason": f"Matches your interest in {hit.title()}", "url": f"/app/circles/{c.pk}/", "icon": "circles", "tile": "t-cyan"})
    for e in event_picks(user, 1):
        picks.append({"kind": "Event", "title": e.title, "reason": f"{e.start_at:%a %d %b} · {e.venue}", "url": f"/app/events/{e.pk}/", "icon": "calendar", "tile": "t-green"})
    top = best_per_mode(user)
    for mode in ("study", "project", "friend"):
        if mode in top:
            r = top[mode]
            picks.append({"kind": engine.MODES[mode]["label"], "title": r["user"].full_name, "reason": r["reasons"][0] if r["reasons"] else "", "url": f"/app/people/{r['user'].pk}/",
                          "icon": engine.MODES[mode]["icon"], "tile": engine.MODES[mode]["tile"], "person": r["user"]})
    # interleave kinds so the strip isn't all one type
    order, seen, mixed = {"Community": 1, "Project": 2, "Circle": 3, "Event": 4}, {}, []
    for p in picks:
        seen[p["kind"]] = seen.get(p["kind"], 0) + 1
        mixed.append((seen[p["kind"]], order.get(p["kind"], 5), p))
    mixed.sort(key=lambda t: (t[0], t[1]))
    return [p for _, _, p in mixed][:8]


def nudges(user):
    """Gentle prompts that unlock better matches. Only about the user's own profile."""
    p, out = user.profile, []
    if not p.match_enabled:
        out.append(("You've turned Campus Match off", "Turn it on to get friend, study and project suggestions.", "/app/me/edit/"))
        return out
    if not p.study_subjects:
        out.append(("Add what you're studying", "Unlocks Study Match.", "/app/me/edit/"))
    if not p.availability:
        out.append(("Tell us when you're free", "Makes matches more practical.", "/app/me/edit/"))
    if not p.skills.all():
        out.append(("Add your skills", "Unlocks Project Match.", "/app/me/edit/"))
    if not p.goals:
        out.append(("Say what you're looking for", "Friends, study partners, teammates…", "/app/me/edit/"))
    return out[:2]
