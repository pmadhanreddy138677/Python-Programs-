from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.communities.models import Community
from apps.moderation.models import Report
from apps.ask.models import AskReport
from apps.notifications.services import notify
from .models import AuditLog, audit
from .services import stats

User = get_user_model()


def admin_only(view):
    """Campus administrators (and superusers) only. Everyone else gets the 403 page."""
    @login_required
    def wrapped(request, *a, **kw):
        if not (request.user.role == "admin" or request.user.is_superuser) or request.user.institution_id is None:
            raise PermissionDenied
        return view(request, *a, **kw)
    wrapped.__name__ = view.__name__
    return wrapped


def _users(request):
    return User.objects.filter(institution_id=request.user.institution_id)


@admin_only
def dashboard(request):
    inst = request.user.institution
    return render(request, "campusadmin/dashboard.html", {"s": stats(inst), "inst": inst,
                  "recent": AuditLog.objects.filter(institution=inst).select_related("actor")[:6],
                  "pending": _users(request).filter(role="faculty", is_approved=False, is_active=True)[:5]})


@admin_only
def users(request):
    qs, g = _users(request), request.GET
    q, role, status = (g.get("q") or "").strip(), g.get("role", ""), g.get("status", "")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
    if role in ("student", "faculty", "admin"):
        qs = qs.filter(role=role)
    if status == "pending":
        qs = qs.filter(role="faculty", is_approved=False)
    elif status == "restricted":
        qs = qs.filter(is_restricted=True)
    elif status == "unverified":
        qs = qs.filter(is_email_verified=False)
    page = Paginator(qs.select_related("department", "profile").order_by("-date_joined"), 20).get_page(g.get("page"))
    params = g.copy(); params.pop("page", None)
    return render(request, "campusadmin/users.html", {"page": page, "q": q, "role": role, "status": status, "querystring": params.urlencode()})


@admin_only
@require_POST
def user_action(request, pk, action):
    target = get_object_or_404(_users(request), pk=pk)
    me = request.user
    if target.pk == me.pk:
        messages.error(request, "You can't do that to your own account.")
        return redirect("campusadmin:users")
    if action == "approve" and target.role == "faculty":
        target.is_approved = True
        target.save(update_fields=["is_approved"])
        notify(target, "announcement", "Your faculty account was approved", "You now have access to faculty features.", "/app/", actor=me)
        audit(me, "faculty_approved", target.email)
    elif action == "reject" and target.role == "faculty" and not target.is_approved:
        target.is_active, target.is_restricted, target.restriction_reason = False, True, "Faculty verification declined"
        target.save(update_fields=["is_active", "is_restricted", "restriction_reason"])
        audit(me, "faculty_rejected", target.email)
    elif action == "restrict":
        if target.role == "admin" or target.is_superuser:
            raise PermissionDenied  # administrators can't be restricted from this screen
        reason = (request.POST.get("reason") or "Policy violation").strip()[:200]
        target.is_active, target.is_restricted, target.restriction_reason = False, True, reason
        target.save(update_fields=["is_active", "is_restricted", "restriction_reason"])
        audit(me, "account_restricted", target.email, reason)
    elif action == "unrestrict" and target.is_restricted:
        target.is_active, target.is_restricted, target.restriction_reason = True, False, ""
        target.save(update_fields=["is_active", "is_restricted", "restriction_reason"])
        audit(me, "account_unrestricted", target.email)
    else:
        raise PermissionDenied
    messages.success(request, "Done.")
    return redirect(request.POST.get("next") if (request.POST.get("next", "").startswith("/app/admin/")) else "campusadmin:users")


@admin_only
def communities(request):
    qs = Community.objects.filter(institution_id=request.user.institution_id).annotate(
        members=Count("memberships", filter=Q(memberships__status="active"), distinct=True)).order_by("-is_official", "name")
    return render(request, "campusadmin/communities.html", {"communities": qs})


@admin_only
@require_POST
def toggle_official(request, pk):
    c = get_object_or_404(Community, pk=pk, institution_id=request.user.institution_id)
    c.is_official = not c.is_official
    c.save(update_fields=["is_official"])
    audit(request.user, "community_official_on" if c.is_official else "community_official_off", c.name)
    return redirect("campusadmin:communities")


@admin_only
def reports(request):
    inst = request.user.institution_id
    return render(request, "campusadmin/reports.html", {
        "community_reports": Report.objects.filter(community__institution_id=inst, status="open").select_related("community", "reporter").order_by("community_id", "-created_at")[:50],
        "ask_open": AskReport.objects.filter(institution_id=inst, status="open").count()})


@admin_only
def audit_log(request):
    page = Paginator(AuditLog.objects.filter(institution_id=request.user.institution_id).select_related("actor"), 25).get_page(request.GET.get("page"))
    return render(request, "campusadmin/audit.html", {"page": page})
