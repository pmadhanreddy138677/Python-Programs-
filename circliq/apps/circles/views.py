from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.services import group_tasks, progress_percent
from apps.notifications.services import notify
from .forms import CircleForm, CirclePostForm, ResourceForm, SessionForm, TaskForm
from .models import CIRCLE_CATEGORIES, Circle, CircleMembership as M, CirclePost, CircleResource, CircleTask, StudySession
from .services import (activate, attach_state, invite_candidates, is_full, join, membership_of, with_counts, with_members)

User = get_user_model()


def _circle(user, pk):
    return get_object_or_404(with_counts(Circle.objects.filter(institution_id=user.institution_id)), pk=pk)


def _member(request, pk):
    c = _circle(request.user, pk)
    m = membership_of(request.user, c)
    if not (m and m.status == "active"):
        raise Http404
    return c, m


def _owner(request, pk):
    c, m = _member(request, pk)
    if m.role != "owner":
        raise Http404
    return c, m


def _back(c, tab):
    return redirect(f"/app/circles/{c.pk}/?tab={tab}")


@login_required
def circle_list(request):
    me = request.user
    tab = request.GET.get("tab", "discover")
    base = with_members(with_counts(Circle.objects.filter(institution_id=me.institution_id)))
    q, cat = (request.GET.get("q") or "").strip(), request.GET.get("category", "")
    invites = list(M.objects.filter(user=me, status="invited").select_related("circle"))
    if tab == "mine":
        qs = base.filter(memberships__user=me, memberships__status="active")
    elif tab == "invites":
        qs = base.filter(memberships__user=me, memberships__status="invited")
    else:
        tab = "discover"
        qs = base.filter(kind="general", status="open")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(purpose__icontains=q))
    if cat in dict(CIRCLE_CATEGORIES):
        qs = qs.filter(category=cat)
    page = Paginator(qs.order_by("-created_at"), 12).get_page(request.GET.get("page"))
    attach_state(me, page.object_list)
    params = request.GET.copy(); params.pop("page", None)
    return render(request, "circles/list.html", {"page": page, "tab": tab, "q": q, "cat": cat, "categories": CIRCLE_CATEGORIES,
                                                  "invite_count": len(invites), "querystring": params.urlencode()})


@login_required
@rate_limit("circle_new", 15, 3600)
def circle_create(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved before you can create circles.")
        return redirect("circles:list")
    form = CircleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            c = form.save(commit=False)
            c.institution, c.created_by = me.institution, me
            c.save()
            M.objects.create(circle=c, user=me, role="owner", status="active")
        messages.success(request, "Your circle is ready. Invite people from the Members tab.")
        return redirect("circles:detail", pk=c.pk)
    return render(request, "circles/form.html", {"form": form, "title": "Create a Circle"})


@login_required
def circle_edit(request, pk):
    c, _ = _owner(request, pk)
    form = CircleForm(request.POST or None, instance=c)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["max_members"] < c.member_count:
            form.add_error("max_members", f"There are already {c.member_count} members.")
        else:
            form.save()
            messages.success(request, "Circle updated.")
            return redirect("circles:detail", pk=c.pk)
    return render(request, "circles/form.html", {"form": form, "title": f"Edit {c.name}", "circle": c})


@login_required
def circle_detail(request, pk):
    me = request.user
    c = _circle(me, pk)
    m = membership_of(me, c)
    member = bool(m and m.status == "active")
    owner = member and m.role == "owner"
    tab = request.GET.get("tab", "discussion")
    ctx = {"c": c, "m": m, "member": member, "owner": owner, "tab": tab, "full": c.member_count >= c.max_members,
           "members_preview": list(M.objects.filter(circle=c, status="active").select_related("user__profile")[:12])}
    if member:
        tasks = list(c.tasks.select_related("assignee__profile"))
        ctx.update(progress=progress_percent(tasks), task_count=len(tasks), columns=group_tasks(tasks))
        now = timezone.now()
        if tab == "tasks":
            ctx["task_form"] = TaskForm(circle=c)
        elif tab == "sessions":
            ctx["upcoming"] = c.sessions.filter(starts_at__gte=now)
            ctx["past"] = c.sessions.filter(starts_at__lt=now).order_by("-starts_at")[:5]
            ctx["session_form"] = SessionForm()
        elif tab == "resources":
            ctx["resources"] = c.resources.select_related("added_by")
            ctx["resource_form"] = ResourceForm()
        elif tab == "members":
            ctx["pending"] = c.memberships.filter(status="pending").select_related("user__profile")
            ctx["invited"] = c.memberships.filter(status="invited").select_related("user__profile")
            ctx["roster"] = list(M.objects.filter(circle=c, status="active").select_related("user__profile", "user__department").order_by("role", "joined_at"))
            if owner:
                ctx["candidates"] = invite_candidates(me, c)
        else:
            ctx["tab"] = "discussion"
            ctx["posts"] = c.posts.select_related("author__profile")[:50]
            ctx["post_form"] = CirclePostForm()
    return render(request, "circles/detail.html", ctx)


@login_required
@require_POST
def circle_join(request, pk):
    c = _circle(request.user, pk)
    m, err = join(request.user, c)
    if err:
        messages.error(request, err)
    elif m.status == "pending":
        messages.success(request, "Request sent. The owner will review it.")
        owner = M.objects.filter(circle=c, role="owner").select_related("user").first()
        if owner:
            notify(owner.user, "circle", f"{request.user.full_name} asked to join {c.name}", url=f"/app/circles/{c.pk}/?tab=members", actor=request.user, ref=f"crj:{c.pk}:{request.user.pk}")
    elif m.status == "active":
        messages.success(request, f"You joined {c.name}!")
    return redirect("circles:detail", pk=c.pk)


@login_required
@require_POST
def circle_leave(request, pk):
    c = _circle(request.user, pk)
    m = membership_of(request.user, c)
    if m is None:
        raise Http404
    if m.role == "owner":
        messages.error(request, "Owners can't leave. Disband the circle instead.")
        return redirect("circles:detail", pk=c.pk)
    m.delete()
    messages.info(request, f"You left {c.name}.")
    return redirect("circles:list")


@login_required
@require_POST
def circle_disband(request, pk):
    c, _ = _owner(request, pk)
    c.delete()
    messages.info(request, "Circle disbanded.")
    return redirect("circles:list")


@login_required
@require_POST
def circle_toggle(request, pk):
    c, _ = _owner(request, pk)
    c.status = "closed" if c.status == "open" else "open"
    c.save(update_fields=["status"])
    messages.info(request, f"Circle is now {c.status}.")
    return redirect("circles:detail", pk=c.pk)


@login_required
@require_POST
def invite(request, pk):
    c, _ = _owner(request, pk)
    target = get_object_or_404(invite_candidates(request.user, c), pk=request.POST.get("user"))  # connections only
    M.objects.get_or_create(circle=c, user=target, defaults={"status": "invited"})
    notify(target, "circle", f"{request.user.full_name} invited you to {c.name}", url=f"/app/circles/{c.pk}/", actor=request.user)
    messages.success(request, f"Invitation sent to {target.full_name}.")
    return _back(c, "members")


@login_required
@require_POST
def respond_invite(request, pk, action):
    c = _circle(request.user, pk)
    m = get_object_or_404(M, circle=c, user=request.user, status="invited")
    if action == "accept":
        _, err = activate(m)
        messages.error(request, err) if err else messages.success(request, f"Welcome to {c.name}!")
    elif action == "decline":
        m.delete()
    else:
        raise Http404
    return redirect("circles:detail", pk=c.pk) if action == "accept" and not err else redirect("circles:list")


@login_required
@require_POST
def member_action(request, pk, mid, action):
    c, _ = _owner(request, pk)
    target = get_object_or_404(M, pk=mid, circle=c)
    if target.role == "owner":
        raise Http404
    if action == "approve" and target.status == "pending":
        _, err = activate(target)
        if err:
            messages.error(request, err)
        else:
            notify(target.user, "circle", f"You're in! Welcome to {c.name}", url=f"/app/circles/{c.pk}/", actor=request.user)
    elif action in ("reject", "remove", "cancel"):
        target.delete()
    else:
        raise Http404
    return _back(c, "members")


# ---- workspace content (active members only) ----
@login_required
@require_POST
def post_new(request, pk):
    c, _ = _member(request, pk)
    f = CirclePostForm(request.POST)
    if f.is_valid():
        p = f.save(commit=False); p.circle, p.author = c, request.user; p.save()
    else:
        messages.error(request, "Write something first.")
    return _back(c, "discussion")


@login_required
@require_POST
def post_delete(request, pk):
    p = get_object_or_404(CirclePost, pk=pk)
    c, m = _member(request, p.circle_id)
    if p.author_id != request.user.id and m.role != "owner":
        raise Http404
    p.delete()
    return _back(c, "discussion")


@login_required
@require_POST
def resource_new(request, pk):
    c, _ = _member(request, pk)
    f = ResourceForm(request.POST)
    if f.is_valid():
        r = f.save(commit=False); r.circle, r.added_by = c, request.user; r.save()
        messages.success(request, "Resource shared.")
    else:
        messages.error(request, "Enter a title and a valid http(s) link.")
    return _back(c, "resources")


@login_required
@require_POST
def resource_delete(request, pk):
    r = get_object_or_404(CircleResource, pk=pk)
    c, m = _member(request, r.circle_id)
    if r.added_by_id != request.user.id and m.role != "owner":
        raise Http404
    r.delete()
    return _back(c, "resources")


@login_required
@require_POST
def session_new(request, pk):
    c, _ = _member(request, pk)
    f = SessionForm(request.POST)
    if f.is_valid():
        s = f.save(commit=False); s.circle, s.created_by = c, request.user; s.save()
        messages.success(request, "Session scheduled.")
    else:
        messages.error(request, "; ".join(e[0] for e in f.errors.values()))
    return _back(c, "sessions")


@login_required
@require_POST
def session_delete(request, pk):
    s = get_object_or_404(StudySession, pk=pk)
    c, m = _member(request, s.circle_id)
    if s.created_by_id != request.user.id and m.role != "owner":
        raise Http404
    s.delete()
    return _back(c, "sessions")


@login_required
@require_POST
def task_new(request, pk):
    c, _ = _member(request, pk)
    f = TaskForm(request.POST, circle=c)
    if f.is_valid() and f.cleaned_data["title"].strip():
        t = f.save(commit=False); t.circle, t.created_by = c, request.user; t.save()
    else:
        messages.error(request, "Give the task a title.")
    return _back(c, "tasks")


@login_required
@require_POST
def task_move(request, pk):
    t = get_object_or_404(CircleTask, pk=pk)
    c, _ = _member(request, t.circle_id)
    status = request.POST.get("status")
    if status not in ("todo", "doing", "done"):
        raise Http404
    t.status = status
    t.save(update_fields=["status"])
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"progress": progress_percent(c.tasks.all())})
    return _back(c, "tasks")


@login_required
@require_POST
def task_delete(request, pk):
    t = get_object_or_404(CircleTask, pk=pk)
    c, m = _member(request, t.circle_id)
    if t.created_by_id != request.user.id and m.role != "owner":
        raise Http404
    t.delete()
    return _back(c, "tasks")
