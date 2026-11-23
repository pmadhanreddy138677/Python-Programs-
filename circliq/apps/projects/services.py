from django.db import transaction
from django.db.models import Count, Prefetch

from .models import Project, ProjectApplication, ProjectMembership as PM


def with_counts(qs):
    return qs.annotate(member_count=Count("memberships", distinct=True))


def with_team(qs):
    return qs.prefetch_related(
        Prefetch("memberships", queryset=PM.objects.select_related("user__profile").order_by("joined_at"), to_attr="team"),
        "required_skills")


def membership_of(user, project):
    return PM.objects.filter(project=project, user=user).first()


def is_full(project):
    return PM.objects.filter(project=project).count() >= project.team_size


def skill_match(user, project):
    mine = {s.pk for s in user.profile.skills.all()}
    req = list(project.required_skills.all())
    have = [s for s in req if s.pk in mine]
    return have, req


def attach_state(user, projects):
    rows = list(projects)
    mem = {m.project_id: m for m in PM.objects.filter(user=user, project__in=rows)}
    apps = {a.project_id: a for a in ProjectApplication.objects.filter(applicant=user, project__in=rows)}
    for p in rows:
        m, a = mem.get(p.id), apps.get(p.id)
        p.state = "lead" if m and m.role == "lead" else "member" if m else (a.status if a else "none")
        p.full = p.member_count >= p.team_size
        have, req = skill_match(user, p)
        p.skills_have = {s.pk for s in have}
        p.match_text = f"You match {len(have)} of {len(req)} skills" if req and have else ""
    return rows


def apply(user, project, message=""):
    """Returns error string or None."""
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project.pk)
        if project.status != "open":
            return "This project isn't recruiting right now."
        if membership_of(user, project):
            return "You're already on this team."
        if is_full(project):
            return "This team is full."
        _, created = ProjectApplication.objects.get_or_create(project=project, applicant=user, defaults={"message": message[:500]})
        if not created:
            return "You've already applied."
    return None


def accept(application):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=application.project_id)
        if is_full(project):
            return "The team is full."
        PM.objects.get_or_create(project=project, user=application.applicant, defaults={"role": "member"})
        application.status = "accepted"
        application.save(update_fields=["status"])
    return None


def recommended_for(user, n=2):
    """Open projects that need skills the user has, best overlap first."""
    out = []
    qs = with_team(with_counts(Project.objects.filter(institution_id=user.institution_id, status="open"))).exclude(memberships__user=user)
    for p in qs[:100]:
        have, req = skill_match(user, p)
        if have and p.member_count < p.team_size:
            p.match_text = f"Needs {', '.join(s.name for s in have[:2])}"
            out.append((len(have), p))
    out.sort(key=lambda t: -t[0])
    return [p for _, p in out[:n]]
