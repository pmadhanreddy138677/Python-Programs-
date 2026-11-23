from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.connections.services import blocked_ids, relations_for
from .matching import compare, profile_sets

User = get_user_model()


def candidate_queryset(me):
    """Students in my institution who allow discovery, excluding me and anyone blocked either way."""
    return (
        User.objects.filter(institution_id=me.institution_id, role="student", is_active=True,
                            is_email_verified=True, profile__is_discoverable=True)
        .exclude(pk=me.pk).exclude(pk__in=blocked_ids(me))
        .select_related("department", "program", "profile")
        .prefetch_related("profile__interests", "profile__skills")
    )


def apply_filters(qs, params):
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(profile__bio__icontains=q))
    for key, field in (("department", "department_id"), ("year", "academic_year"),
                       ("skill", "profile__skills__id"), ("interest", "profile__interests__id")):
        val = params.get(key)
        if val and val.isdigit():
            qs = qs.filter(**{field: int(val)})
    return qs.distinct()


def ranked(me, qs, limit=500):
    me_sets = profile_sets(me.profile)
    rows = []
    for u in qs[:limit]:
        score, why, shared = compare(me, u, me_sets)
        rows.append({"user": u, "score": score, "why": why, "shared": shared})
    rows.sort(key=lambda r: (-r["score"], r["user"].full_name.lower()))
    return rows


def suggestions(me, n=3):
    rows = [r for r in ranked(me, candidate_queryset(me), limit=200) if r["score"] > 0][:n]
    rel = relations_for(me, [r["user"].id for r in rows])
    for r in rows:
        r["rel"], r["conn"] = rel.get(r["user"].id, ("none", None))
    return rows
