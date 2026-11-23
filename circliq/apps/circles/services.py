from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from apps.connections.models import Connection
from apps.connections.services import blocked_ids
from .models import Circle, CircleMembership as M, StudySession


def with_counts(qs):
    return qs.annotate(member_count=Count("memberships", filter=Q(memberships__status="active"), distinct=True))


def with_members(qs):
    return qs.prefetch_related(Prefetch("memberships", queryset=M.objects.filter(status="active").select_related("user__profile").order_by("joined_at"), to_attr="active_members"))


def membership_of(user, circle):
    return M.objects.filter(circle=circle, user=user).first()


def is_full(circle):
    return M.objects.filter(circle=circle, status="active").count() >= circle.max_members


def attach_state(user, circles):
    rows = list(circles)
    mm = {m.circle_id: m for m in M.objects.filter(user=user, circle__in=rows)}
    for c in rows:
        m = mm.get(c.id)
        c.state = "none" if not m else {"active": "member", "pending": "pending", "invited": "invited"}[m.status]
        c.my_role = m.role if m else None
        c.full = getattr(c, "member_count", 0) >= c.max_members
    return rows


def join(user, circle):
    """Returns (membership, error). Capacity is checked inside a transaction (row-locked on PostgreSQL)."""
    with transaction.atomic():
        circle = Circle.objects.select_for_update().get(pk=circle.pk)
        existing = membership_of(user, circle)
        if existing and existing.status == "active":
            return existing, None
        if circle.status != "open":
            return None, "This circle is closed to new members."
        if existing and existing.status == "pending":
            return existing, None
        if existing and existing.status == "invited":
            return _activate(existing, circle)
        if circle.join_policy == "approval":
            return M.objects.create(circle=circle, user=user, status="pending"), None
        if is_full(circle):
            return None, "This circle is full."
        return M.objects.create(circle=circle, user=user, status="active"), None


def _activate(m, circle):
    if is_full(circle):
        return None, "This circle is full."
    m.status = "active"
    m.save(update_fields=["status"])
    return m, None


def activate(m):
    with transaction.atomic():
        circle = Circle.objects.select_for_update().get(pk=m.circle_id)
        return _activate(m, circle)


def invite_candidates(user, circle):
    """Accepted connections who aren't already in the circle and aren't blocked."""
    ids = set()
    for c in Connection.objects.filter(Q(requester=user) | Q(receiver=user), status="accepted"):
        ids.add(c.other(user).id)
    ids -= blocked_ids(user)
    ids -= set(M.objects.filter(circle=circle).values_list("user_id", flat=True))
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(pk__in=ids, institution_id=circle.institution_id, is_active=True).select_related("profile")


def upcoming_sessions(user, n=3):
    ids = M.objects.filter(user=user, status="active").values_list("circle_id", flat=True)
    return StudySession.objects.filter(circle_id__in=ids, starts_at__gte=timezone.now()).select_related("circle")[:n]
