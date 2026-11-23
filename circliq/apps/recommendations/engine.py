"""Campus Match: transparent weighted scoring on information students chose to provide.

No sensitive attributes, no hidden signals, no paid AI. Every point of score maps to a human-readable reason.
"""
from dataclasses import dataclass, field

from apps.profiles.matching import human_join
from apps.profiles.models import AVAILABILITY, GOAL_PHRASES, Interest

HOBBY_CATEGORIES = {"Lifestyle", "Sports", "Creative"}
SLOT = dict(AVAILABILITY)

MODES = {
    "friend": {"label": "Friend Match", "tagline": "People who share your hobbies and interests", "ref": 18, "tile": "t-violet", "icon": "heart"},
    "study": {"label": "Study Match", "tagline": "People studying the same subjects", "ref": 22, "tile": "t-cyan", "icon": "book"},
    "project": {"label": "Project Match", "tagline": "People whose skills complement yours", "ref": 20, "tile": "t-amber", "icon": "code"},
}


@dataclass
class Features:
    interests: set = field(default_factory=set)
    hobbies: set = field(default_factory=set)
    tech: set = field(default_factory=set)
    skills: set = field(default_factory=set)
    goals: set = field(default_factory=set)
    subjects: dict = field(default_factory=dict)  # lowercase -> original spelling
    availability: set = field(default_factory=set)
    collab: set = field(default_factory=set)
    dept: int = None
    year: int = None


@dataclass
class Result:
    score: int = 0
    reasons: list = field(default_factory=list)


def category_map():
    return dict(Interest.objects.values_list("name", "category"))


def features_of(user, cats):
    p = user.profile
    interests = {i.name for i in p.interests.all()}
    return Features(
        interests=interests,
        hobbies={n for n in interests if cats.get(n) in HOBBY_CATEGORIES},
        tech={n for n in interests if cats.get(n) == "Technology"},
        skills={s.name for s in p.skills.all()},
        goals=set(p.goals or []),
        subjects={s.lower(): s for s in p.subject_list()},
        availability=set(p.availability or []), collab=set(p.collab_preferences or []),
        dept=user.department_id, year=user.academic_year)


def _slots(a, b, cap):
    shared = sorted(a & b, key=lambda k: list(SLOT).index(k) if k in SLOT else 99)[:cap]
    return shared


def friend(me, o):
    r = Result()
    shared = sorted(me.interests & o.interests)
    if shared:
        bonus = len(me.hobbies & o.hobbies)
        r.score += 3 * len(shared) + bonus
        r.reasons.append(f"You both enjoy {human_join(shared[:3])}")
    if "friends" in me.goals and "friends" in o.goals:
        r.score += 4
        r.reasons.append("You're both looking to make new friends")
    times = _slots(me.availability, o.availability, 3)
    if times:
        r.score += len(times)
        r.reasons.append(f"You're both free {human_join([SLOT[t].lower() for t in times[:2]])}")
    if me.year and me.year == o.year:
        r.score += 1
        r.reasons.append(f"You're both in Year {me.year}")
    return r if shared or "friends" in me.goals and "friends" in o.goals else Result()


def study(me, o):
    r = Result()
    shared = sorted(set(me.subjects) & set(o.subjects))
    if shared:
        r.score += 6 * min(len(shared), 3)
        r.reasons.append(f"You're both studying {human_join([me.subjects[s] for s in shared[:3]])}")
    both_goal = "study" in me.goals and "study" in o.goals
    if both_goal:
        r.score += 4
        r.reasons.append("You both want study partners")
    times = _slots(me.availability, o.availability, 3)
    if times and (shared or both_goal):
        r.score += 2 * len(times)
        r.reasons.append(f"You're both free {human_join([SLOT[t].lower() for t in times[:2]])}")
    if r.score:
        if me.dept and me.dept == o.dept:
            r.score += 1
            r.reasons.append("Same department")
        if me.year and me.year == o.year:
            r.score += 1
            r.reasons.append(f"Both in Year {me.year}")
    return r if shared or both_goal else Result()


def project(me, o):
    r = Result()
    complement = sorted(o.skills - me.skills)
    if complement:
        r.score += 2 * min(len(complement), 4)
        r.reasons.append(f"Brings {human_join(complement[:3])}, which you don't list")
    shared = sorted(me.skills & o.skills)
    if shared:
        r.score += min(len(shared), 3)
        r.reasons.append(f"You both know {human_join(shared[:3])}")
    if "projects" in me.goals and "projects" in o.goals:
        r.score += 4
        r.reasons.append("You're both looking for project teammates")
    collab = sorted(me.collab & o.collab)
    if collab:
        r.score += min(len(collab), 3)
        r.reasons.append("You both like " + human_join([c.replace("_", " ") for c in collab[:2]]))
    tech = sorted(me.tech & o.tech)
    if tech:
        r.score += min(len(tech), 3)
        r.reasons.append(f"Shared interest in {human_join(tech[:2])}")
    times = _slots(me.availability, o.availability, 2)
    if times and r.score:
        r.score += len(times)
        r.reasons.append(f"You're both free {human_join([SLOT[t].lower() for t in times[:1]])}")
    return r if complement or ("projects" in me.goals and "projects" in o.goals) else Result()


SCORERS = {"friend": friend, "study": study, "project": project}


def strength(mode, score):
    return min(100, round(100 * score / MODES[mode]["ref"]))


def label(pct):
    return "Great match" if pct >= 70 else "Good match" if pct >= 40 else "Worth a look"
