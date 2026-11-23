from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.institutions.models import Department
from apps.notifications.services import notify, notify_many
from .forms import AnnouncementForm, FacultyProfileForm, MentorshipForm
from .models import Announcement, FacultyProfile, MentorshipRequest

User = get_user_model()


def _is_faculty(u):
    return u.role == "faculty" and u.is_approved


def _can_announce(u):
    return _is_faculty(u) or u.role == "admin" or u.is_superuser


def _faculty_qs(me):
    return User.objects.filter(institution_id=me.institution_id, role="faculty", is_approved=True, is_active=True).select_related("faculty_profile", "department", "profile")


@login_required
def directory(request):
    me = request.user
    qs = _faculty_qs(me)
    g = request.GET
    q, dept, mentor = (g.get("q") or "").strip(), g.get("department", ""), g.get("mentorship", "")
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(faculty_profile__expertise__icontains=q) | Q(faculty_profile__research_interests__icontains=q))
    if dept.isdigit():
        qs = qs.filter(department_id=int(dept))
    if mentor == "1":
        qs = qs.filter(faculty_profile__accepts_mentorship=True)
    page = Paginator(qs.order_by("full_name"), 12).get_page(g.get("page"))
    params = g.copy(); params.pop("page", None)
    return render(request, "faculty/directory.html", {"page": page, "q": q, "dept": dept, "mentor": mentor,
                  "departments": Department.objects.filter(institution_id=me.institution_id), "querystring": params.urlencode()})


@login_required
def faculty_detail(request, pk):
    me = request.user
    f = get_object_or_404(_faculty_qs(me), pk=pk)
    from apps.messaging.services import can_message
    from apps.projects.models import Project
    prof = f.faculty_profile
    existing = MentorshipRequest.objects.filter(student=me, faculty=f).first()
    return render(request, "faculty/detail.html", {
        "f": f, "fp": prof, "can_dm": can_message(me, f), "form": MentorshipForm(),
        "can_request": me.role == "student" and prof.accepts_mentorship and not MentorshipRequest.objects.filter(student=me, faculty=f, status="pending").exists(),
        "latest_request": existing, "is_me": me.pk == f.pk,
        "opportunities": Project.objects.filter(creator=f, institution_id=me.institution_id, kind__in=("mentorship", "research"), status="open")[:5],
        "announcements": Announcement.objects.filter(author=f)[:3]})


@login_required
def my_faculty_profile(request):
    if not _is_faculty(request.user):
        raise Http404
    prof, _ = FacultyProfile.objects.get_or_create(user=request.user)
    form = FacultyProfileForm(request.POST or None, instance=prof)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Faculty profile updated.")
        return redirect("faculty:detail", pk=request.user.pk)
    return render(request, "faculty/edit.html", {"form": form})


@login_required
@require_POST
@rate_limit("mentor", 10, 86400)
def request_mentorship(request, pk):
    me = request.user
    f = get_object_or_404(_faculty_qs(me), pk=pk)
    if me.role != "student" or not f.faculty_profile.accepts_mentorship:
        raise Http404
    form = MentorshipForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():  # savepoint, so a duplicate can't poison the surrounding transaction
                MentorshipRequest.objects.create(student=me, faculty=f, message=form.cleaned_data["message"])
        except IntegrityError:
            messages.info(request, "You already have a pending request with this faculty member.")
        else:
            notify(f, "mentorship", f"{me.full_name} asked for mentorship", form.cleaned_data["message"][:120], "/app/faculty/requests/", actor=me)
            messages.success(request, "Request sent. You'll be notified when they respond.")
    else:
        messages.error(request, "Please write a short message.")
    return redirect("faculty:detail", pk=f.pk)


@login_required
def requests_page(request):
    me = request.user
    received = MentorshipRequest.objects.filter(faculty=me).select_related("student__profile", "student__department") if _is_faculty(me) else []
    sent = MentorshipRequest.objects.filter(student=me).select_related("faculty__profile")
    return render(request, "faculty/requests.html", {"received": received, "sent": sent})


@login_required
@require_POST
def respond_mentorship(request, pk, action):
    r = get_object_or_404(MentorshipRequest, pk=pk, faculty=request.user, status="pending")  # only the faculty member addressed
    if action not in ("accept", "decline"):
        raise Http404
    r.status = "accepted" if action == "accept" else "declined"
    r.responded_at = timezone.now()
    r.save(update_fields=["status", "responded_at"])
    verb = "accepted" if action == "accept" else "declined"
    notify(r.student, "mentorship", f"{request.user.full_name} {verb} your mentorship request", url=f"/app/faculty/{request.user.pk}/", actor=request.user)
    return redirect("faculty:requests")


@login_required
def announcements(request):
    me = request.user
    page = Paginator(Announcement.objects.filter(institution_id=me.institution_id).select_related("author__profile"), 10).get_page(request.GET.get("page"))
    return render(request, "faculty/announcements.html", {"page": page, "can_post": _can_announce(me)})


@login_required
@rate_limit("announce", 10, 3600)
def announcement_new(request):
    me = request.user
    if not _can_announce(me):
        raise Http404
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        a.institution, a.author = me.institution, me
        a.save()
        recipients = list(User.objects.filter(institution_id=me.institution_id, is_active=True).exclude(pk=me.pk))
        notify_many(recipients, "announcement", f"Announcement: {a.title}", a.body[:150], "/app/faculty/announcements/", actor=me)
        messages.success(request, f"Announcement published to {len(recipients)} people.")
        return redirect("faculty:announcements")
    return render(request, "faculty/announcement_form.html", {"form": form})


@login_required
@require_POST
def announcement_delete(request, pk):
    a = get_object_or_404(Announcement, pk=pk, institution_id=request.user.institution_id)
    if a.author_id != request.user.id and not (request.user.role == "admin" or request.user.is_superuser):
        raise Http404
    a.delete()
    return redirect("faculty:announcements")
