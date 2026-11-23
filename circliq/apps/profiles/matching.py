"""Deterministic, explainable matching using only voluntarily supplied profile data."""
from .models import GOAL_PHRASES


def human_join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def profile_sets(profile):
    return (
        {i.name for i in profile.interests.all()},
        {s.name for s in profile.skills.all()},
        set(profile.goals or []),
    )


def compare(me, other, me_sets=None):
    """Return (score, explanation, shared_interest_names) for another user's profile."""
    mi, ms, mg = me_sets or profile_sets(me.profile)
    oi, os_, og = profile_sets(other.profile)
    si, ss, sg = sorted(mi & oi), sorted(ms & os_), sorted(mg & og)
    score = 3 * len(si) + 2 * len(ss) + 2 * len(sg) + (1 if me.department_id and me.department_id == other.department_id else 0)
    if si:
        text = f"You both enjoy {human_join(si[:3])}."
    elif ss:
        text = f"You both know {human_join(ss[:3])}."
    elif sg:
        text = f"Both of you are looking for {GOAL_PHRASES.get(sg[0], sg[0])}."
    else:
        text = ""
    return score, text, set(si)
