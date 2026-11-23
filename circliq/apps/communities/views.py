from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.moderation.models import ModerationAction, Report
from apps.notifications.services import notify
from .forms import CommunityForm
from .models import CATEGORIES, Community, CommunityMembership as M
from .services import (attach_state, can_manage, can_view_content, institution_communities, is_active_member,
                       join, membership_of, with_counts)


def _community_or_404(user, pk):
    """Communities are always looked up inside the user's own institution."""
    return get_object_or_404(with_counts(Community.objects.filter(institution_id=user.institution_id)), pk=pk)


@login_required
def community_list(request):
    me = request.user
    qs = institution_communities(me)
    cat, q, scope = request.GET.get("category", ""), (request.GET.get("q") or "").strip(), request.GET.get("scope", "")
    if cat in dict(CATEGORIES):
        qs = qs.filter(category=cat)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if scope == "mine":
        qs = qs.filter(memberships__user=me, memberships__status="active")
    page = Paginator(qs.order_by("-is_official", "-member_count", "name"), 12).get_page(request.GET.get("page"))
    attach_state(me, page.object_list)
    params = request.GET.copy(); params.pop("page", None)
    return render(request, "communities/list.html", {
        "page": page, "categories": CATEGORIES, "cat": cat, "q": q, "scope": scope, "querystring": params.urlencode()})


@login_required
@rate_limit("community_new", 15, 3600)
def community_create(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved before you can create communities.")
        return redirect("communities:list")
    form = CommunityForm(request.POST or None, request.FILES or None, institution=me.institution)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            c = form.save(commit=False)
            c.institution, c.created_by = me.institution, me
            c.save()
            M.objects.create(community=c, user=me, role="owner", status="active")
        messages.success(request, f"{c.name} is live! Invite people and start a discussion.")
        return redirect("communities:detail", pk=c.pk)
    return render(request, "communities/form.html", {"form": form, "title": "Create a community"})


@login_required
def community_edit(request, pk):
    c = _community_or_404(request.user, pk)
    if not can_manage(request.user, c):
        raise Http404
    form = CommunityForm(request.POST or None, request.FILES or None, instance=c, institution=c.institution)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Community updated.")
        return redirect("communities:detail", pk=c.pk)
    return render(request, "communities/form.html", {"form": form, "title": f"Edit {c.name}", "community": c})


@login_required
def community_detail(request, pk):
    from apps.discussions.feed import annotate_posts
    from apps.discussions.forms import PostForm
    from apps.discussions.models import Post
    me = request.user
    c = _community_or_404(me, pk)
    m = membership_of(me, c)
    manage = can_manage(me, c)
    allowed = can_view_content(me, c)
    tab = request.GET.get("tab", "discussions")
    ctx = {"c": c, "m": m, "manage": manage, "allowed": allowed, "tab": tab,
           "is_member": bool(m and m.status == "active"), "pending": bool(m and m.status == "pending")}
    if manage:
        ctx["open_reports"] = Report.objects.filter(community=c, status="open").count()
        ctx["pending_members"] = c.memberships.filter(status="pending").count()
    if allowed:
        if tab in ("discussions", "questions"):
            posts = Post.objects.filter(community=c, is_removed=False).select_related("author__profile", "author__department", "community")
            posts = posts.filter(kind="question") if tab == "questions" else posts.exclude(kind="question")
            q = (request.GET.get("q") or "").strip()
            if q:
                posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q))
            ctx["page"] = Paginator(annotate_posts(posts, me).order_by("-created_at"), 10).get_page(request.GET.get("page"))
            ctx["q"] = q
            ctx["form"] = PostForm(initial={"kind": "question" if tab == "questions" else "discussion", "community": c.pk}, user=me)
        elif tab == "members":
            ctx["members"] = c.memberships.filter(status="active").select_related("user__profile", "user__department").order_by("role", "user__full_name")
        else:
            ctx["tab"] = "about"
    if manage and tab == "members":
        ctx["pending_list"] = c.memberships.filter(status="pending").select_related("user__profile")
    return render(request, "communities/detail.html", ctx)


@login_required
@require_POST
def community_join(request, pk):
    c = _community_or_404(request.user, pk)
    m, created = join(request.user, c)
    if created:
        messages.success(request, "Request sent. A moderator will review it." if m.status == "pending" else f"Welcome to {c.name}!")
        if m.status == "pending":
            for mgr in M.objects.filter(community=c, status="active", role__in=("owner", "moderator")).select_related("user"):
                notify(mgr.user, "community", f"{request.user.full_name} asked to join {c.name}", url=f"/app/communities/{c.pk}/?tab=members", actor=request.user, ref=f"cj:{c.pk}")
    return redirect(request.POST.get("next_url") if request.POST.get("next_url", "").startswith("/app/") else reverse_detail(c))


def reverse_detail(c):
    from django.urls import reverse
    return reverse("communities:detail", args=[c.pk])


@login_required
@require_POST
def community_leave(request, pk):
    c = _community_or_404(request.user, pk)
    m = membership_of(request.user, c)
    if m is None:
        raise Http404
    if m.role == "owner":
        messages.error(request, "Owners can't leave. Ask a moderator to take over first, or contact an admin.")
        return redirect("communities:detail", pk=c.pk)
    m.delete()
    messages.info(request, f"You left {c.name}.")
    return redirect("communities:list")


@login_required
@require_POST
def member_action(request, pk, mid, action):
    me = request.user
    c = _community_or_404(me, pk)
    if not can_manage(me, c):
        raise Http404
    target = get_object_or_404(M, pk=mid, community=c)
    is_owner = M.objects.filter(community=c, user=me, role="owner").exists() or me.is_superuser or me.role == "admin"
    if action == "approve" and target.status == "pending":
        target.status = "active"; target.save(update_fields=["status"])
        notify(target.user, "community", f"You're in! Welcome to {c.name}", url=f"/app/communities/{c.pk}/", actor=me)
    elif action == "reject" and target.status == "pending":
        target.delete()
    elif action == "remove" and target.role == "member":
        target.delete()
    elif action == "promote" and is_owner and target.role == "member" and target.status == "active":
        target.role = "moderator"; target.save(update_fields=["role"])
    elif action == "demote" and is_owner and target.role == "moderator":
        target.role = "member"; target.save(update_fields=["role"])
    else:
        raise Http404
    ModerationAction.objects.create(community=c, moderator=me, action=f"member_{action}", note=f"user {target.user_id}")
    messages.success(request, "Done.")
    return redirect(f"{reverse_detail(c)}?tab=members")


@login_required
@require_POST
def toggle_official(request, pk):
    """Only campus admins (or superusers) can grant or revoke official status."""
    me = request.user
    c = _community_or_404(me, pk)
    if not (me.is_superuser or (me.role == "admin" and me.institution_id == c.institution_id)):
        raise Http404
    c.is_official = not c.is_official
    c.save(update_fields=["is_official"])
    ModerationAction.objects.create(community=c, moderator=me, action="official_on" if c.is_official else "official_off")
    messages.success(request, "Official status updated.")
    return redirect("communities:detail", pk=c.pk)
