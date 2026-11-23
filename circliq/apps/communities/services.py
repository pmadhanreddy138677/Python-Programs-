from django.db.models import Count, Q

from .models import Community, CommunityMembership as M

# Interest name -> community category, used for explainable recommendations.
INTEREST_CATEGORY = {
    "Python": "technology", "Artificial Intelligence": "technology", "Machine Learning": "technology",
    "Web Development": "technology", "Cybersecurity": "technology", "Robotics": "technology", "Data Science": "technology",
    "Gaming": "gaming", "Anime": "gaming", "Cricket": "sports", "Football": "sports", "Badminton": "sports",
    "Basketball": "sports", "Fitness": "sports", "Music": "music", "Photography": "arts", "Design": "arts",
    "Video Editing": "arts", "Art": "arts", "Writing": "arts", "Entrepreneurship": "entrepreneurship",
    "Finance": "entrepreneurship", "Public Speaking": "entrepreneurship", "Reading": "academics",
}


def with_counts(qs):
    return qs.annotate(member_count=Count("memberships", filter=Q(memberships__status="active"), distinct=True))


def institution_communities(user):
    return with_counts(Community.objects.filter(institution_id=user.institution_id))


def membership_of(user, community):
    return M.objects.filter(community=community, user=user).first()


def is_active_member(user, community):
    return M.objects.filter(community=community, user=user, status="active").exists()


def can_manage(user, community):
    """Owner/moderator of the community, or a campus admin of the same institution."""
    if user.is_superuser:
        return True
    if user.role == "admin" and user.institution_id == community.institution_id:
        return True
    return M.objects.filter(community=community, user=user, status="active", role__in=("owner", "moderator")).exists()


def can_view_content(user, community):
    if user.institution_id != community.institution_id and not user.is_superuser:
        return False
    return (not community.is_private) or is_active_member(user, community) or can_manage(user, community)


def join(user, community):
    """Public: instant membership. Private: pending until a manager approves."""
    status = "pending" if community.is_private else "active"
    m, created = M.objects.get_or_create(community=community, user=user, defaults={"status": status})
    return m, created


def my_active_ids(user):
    return set(M.objects.filter(user=user, status="active").values_list("community_id", flat=True))


def attach_state(user, communities):
    """Annotate each community in an iterable with .state (member|pending|none) and .my_role."""
    rows = list(communities)
    mm = {m.community_id: m for m in M.objects.filter(user=user, community__in=rows)}
    for c in rows:
        m = mm.get(c.id)
        c.state = "none" if not m else ("member" if m.status == "active" else "pending")
        c.my_role = m.role if m else None
    return rows


def recommend(user, n=4):
    """Communities (not yet joined) matching the user's interests; ties broken by size."""
    cats = {INTEREST_CATEGORY[i.name] for i in user.profile.interests.all() if i.name in INTEREST_CATEGORY}
    names = [i.name.lower() for i in user.profile.interests.all()]
    joined = set(M.objects.filter(user=user).values_list("community_id", flat=True))
    out = []
    for c in institution_communities(user).filter(visibility="public").exclude(pk__in=joined):
        text = f"{c.name} {c.description}".lower()
        hits = [nm for nm in names if nm in text]
        score = 3 * len(hits) + (2 if c.category in cats else 0)
        if score:
            c.reason = f"Matches your interest in {hits[0].title()}" if hits else f"Popular in {c.get_category_display()}"
            out.append((score, c.member_count, c))
    out.sort(key=lambda t: (-t[0], -t[1], t[2].name))
    return attach_state(user, [c for _, _, c in out[:n]])
