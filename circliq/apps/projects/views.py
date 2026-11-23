from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.services import group_tasks, progress_percent
from apps.notifications.services import notify
from apps.profiles.models import Skill
from .forms import ApplicationForm, ProjectCommentForm, ProjectForm, ProjectTaskForm
from .models import PROJECT_CATEGORIES, Project, ProjectApplication, ProjectComment, ProjectMembership as PM, ProjectTask
from .services import accept, apply, attach_state, membership_of, skill_match, with_counts, with_team


def _project(user, pk):
    return get_object_or_404(with_counts(Project.objects.filter(institution_id=user.institution_id)), pk=pk)


def _member(request, pk):
    p = _project(request.user, pk)
    m = membership_of(request.user, p)
    if m is None:
        raise Http404
    return p, m


def _lead(request, pk):
    p, m = _member(request, pk)
    if m.role != "lead":
        raise Http404
    return p, m


def _back(p, tab):
    return redirect(f"/app/projects/{p.pk}/?tab={tab}")


@login_required
def project_list(request):
    me = request.user
    qs = with_team(with_counts(Project.objects.filter(institution_id=me.institution_id)).select_related("creator__profile"))
    g = request.GET
    q, cat, status, skill, scope, kind = (g.get("q") or "").strip(), g.get("category", ""), g.get("status", "open"), g.get("skill", ""), g.get("scope", ""), g.get("kind", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(technologies__icontains=q))
    if cat in dict(PROJECT_CATEGORIES):
        qs = qs.filter(category=cat)
    if kind in dict(Project.Kind.choices):
        qs = qs.filter(kind=kind)
    if status in dict(Project.Status.choices):
        qs = qs.filter(status=status)
    if skill.isdigit():
        qs = qs.filter(required_skills__id=int(skill))
    if scope == "mine":
        qs = qs.filter(memberships__user=me)
    page = Paginator(qs.distinct().order_by("-created_at"), 12).get_page(g.get("page"))
    attach_state(me, page.object_list)
    params = g.copy(); params.pop("page", None)
    return render(request, "projects/list.html", {
        "page": page, "q": q, "cat": cat, "status": status, "skill": skill, "scope": scope, "kind": kind,
        "categories": PROJECT_CATEGORIES, "statuses": Project.Status.choices, "kinds": Project.Kind.choices,
        "skills": Skill.objects.all(), "querystring": params.urlencode()})


@login_required
@rate_limit("project_new", 10, 3600)
def project_create(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved before you can post projects.")
        return redirect("projects:list")
    form = ProjectForm(request.POST or None, user=me)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            p = form.save(commit=False)
            p.institution, p.creator = me.institution, me
            p.save()
            form.save_m2m()
            PM.objects.create(project=p, user=me, role="lead")
        messages.success(request, "Project posted. Applications will appear in your workspace.")
        return redirect("projects:detail", pk=p.pk)
    return render(request, "projects/form.html", {"form": form, "title": "Post a project"})


@login_required
def project_edit(request, pk):
    p, _ = _lead(request, pk)
    form = ProjectForm(request.POST or None, instance=p, user=request.user)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["team_size"] < p.member_count:
            form.add_error("team_size", f"The team already has {p.member_count} members.")
        else:
            form.save()
            messages.success(request, "Project updated.")
            return redirect("projects:detail", pk=p.pk)
    return render(request, "projects/form.html", {"form": form, "title": f"Edit {p.title}", "project": p})


@login_required
def project_detail(request, pk):
    me = request.user
    p = _project(me, pk)
    m = membership_of(me, p)
    member, lead = m is not None, bool(m and m.role == "lead")
    team = list(p.memberships.select_related("user__profile", "user__department").order_by("joined_at"))
    have, req = skill_match(me, p)
    my_app = ProjectApplication.objects.filter(project=p, applicant=me).first()
    tab = request.GET.get("tab", "overview")
    ctx = {"status_choices": Project.Status.choices, "p": p, "m": m, "member": member, "lead": lead, "team": team, "tab": tab, "full": p.member_count >= p.team_size,
           "skills_have": {s.pk for s in have}, "my_app": my_app, "app_form": ApplicationForm(),
           "pending_count": p.applications.filter(status="pending").count() if lead else 0}
    if member:
        tasks = list(p.tasks.select_related("assignee__profile"))
        ctx.update(progress=progress_percent(tasks), task_count=len(tasks), columns=group_tasks(tasks))
        if tab == "tasks":
            ctx["task_form"] = ProjectTaskForm(project=p)
        elif tab == "discussion":
            ctx["comments"] = p.comments.select_related("author__profile")[:50]
            ctx["comment_form"] = ProjectCommentForm()
        elif tab == "applications" and lead:
            ctx["applications"] = p.applications.select_related("applicant__profile", "applicant__department").order_by("status", "-created_at")
        else:
            ctx["tab"] = "overview"
    else:
        ctx["tab"] = "overview"
        ctx["progress"] = progress_percent(p.tasks.all())
    return render(request, "projects/detail.html", ctx)


@login_required
@require_POST
@rate_limit("project_apply", 30, 3600)
def project_apply(request, pk):
    p = _project(request.user, pk)
    err = apply(request.user, p, request.POST.get("message", ""))
    if err:
        messages.error(request, err)
    else:
        messages.success(request, "Application sent. The project lead will review it.")
        notify(p.creator, "project", f"{request.user.full_name} applied to {p.title}", url=f"/app/projects/{p.pk}/?tab=applications", actor=request.user, ref=f"pa:{p.pk}")
    return redirect("projects:detail", pk=p.pk)


@login_required
@require_POST
def project_withdraw(request, pk):
    p = _project(request.user, pk)
    ProjectApplication.objects.filter(project=p, applicant=request.user, status="pending").delete()
    messages.info(request, "Application withdrawn.")
    return redirect("projects:detail", pk=p.pk)


@login_required
@require_POST
def application_action(request, pk, action):
    a = get_object_or_404(ProjectApplication.objects.select_related("project"), pk=pk, status="pending")
    p, _ = _lead(request, a.project_id)
    if action == "accept":
        err = accept(a)
        if err:
            messages.error(request, err)
        else:
            messages.success(request, f"{a.applicant.full_name} joined the team.")
            notify(a.applicant, "project", f"You're on the team: {p.title}", url=f"/app/projects/{p.pk}/", actor=request.user)
    elif action == "reject":
        a.status = "rejected"; a.save(update_fields=["status"])
        notify(a.applicant, "project", f"Update on your application to {p.title}", "The lead chose other applicants this time.", f"/app/projects/{p.pk}/", actor=request.user)
    else:
        raise Http404
    return _back(p, "applications")


@login_required
@require_POST
def member_remove(request, pk, mid):
    p, _ = _lead(request, pk)
    t = get_object_or_404(PM, pk=mid, project=p)
    if t.role == "lead":
        raise Http404
    t.delete()
    return _back(p, "overview")


@login_required
@require_POST
def project_leave(request, pk):
    p, m = _member(request, pk)
    if m.role == "lead":
        messages.error(request, "The lead can't leave. Close the project or ask the team to continue elsewhere.")
        return redirect("projects:detail", pk=p.pk)
    m.delete()
    messages.info(request, "You left the project.")
    return redirect("projects:list")


@login_required
@require_POST
def project_status(request, pk):
    p, _ = _lead(request, pk)
    s = request.POST.get("status")
    if s not in dict(Project.Status.choices):
        raise Http404
    p.status = s
    p.save(update_fields=["status"])
    messages.success(request, "Status updated.")
    return _back(p, "overview")


@login_required
@require_POST
def task_new(request, pk):
    p, _ = _member(request, pk)
    f = ProjectTaskForm(request.POST, project=p)
    if f.is_valid() and f.cleaned_data["title"].strip():
        t = f.save(commit=False); t.project, t.created_by = p, request.user; t.save()
    else:
        messages.error(request, "Give the task a title.")
    return _back(p, "tasks")


@login_required
@require_POST
def task_move(request, pk):
    t = get_object_or_404(ProjectTask, pk=pk)
    p, _ = _member(request, t.project_id)
    if request.POST.get("status") not in ("todo", "doing", "done"):
        raise Http404
    t.status = request.POST["status"]
    t.save(update_fields=["status"])
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"progress": progress_percent(p.tasks.all())})
    return _back(p, "tasks")


@login_required
@require_POST
def task_delete(request, pk):
    t = get_object_or_404(ProjectTask, pk=pk)
    p, m = _member(request, t.project_id)
    if t.created_by_id != request.user.id and m.role != "lead":
        raise Http404
    t.delete()
    return _back(p, "tasks")


@login_required
@require_POST
def comment_new(request, pk):
    p, _ = _member(request, pk)
    f = ProjectCommentForm(request.POST)
    if f.is_valid() and f.cleaned_data["body"].strip():
        c = f.save(commit=False); c.project, c.author = p, request.user; c.save()
    return _back(p, "discussion")


@login_required
@require_POST
def comment_delete(request, pk):
    c = get_object_or_404(ProjectComment, pk=pk)
    p, m = _member(request, c.project_id)
    if c.author_id != request.user.id and m.role != "lead":
        raise Http404
    c.delete()
    return _back(p, "discussion")
