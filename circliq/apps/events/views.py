from apps.core.ratelimit import rate_limit
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.communities.models import CATEGORIES
from .forms import EventForm
from .models import Event, EventRegistration as Reg, EventSave


def _qs(user):
    return Event.objects.filter(institution_id=user.institution_id).annotate(
        going=Count("registrations", distinct=True),
        i_go=Exists(Reg.objects.filter(event=OuterRef("pk"), user=user)),
        i_saved=Exists(EventSave.objects.filter(event=OuterRef("pk"), user=user)))


def _event(user, pk):
    return get_object_or_404(_qs(user).select_related("organizer__profile"), pk=pk)


def _can_edit(user, e):
    return e.organizer_id == user.id or user.role == "admin" or user.is_superuser


@login_required
def event_list(request):
    me, g = request.user, request.GET
    tab, q, cat = g.get("tab", "upcoming"), (g.get("q") or "").strip(), g.get("category", "")
    qs = _qs(me).select_related("organizer__profile")
    now = timezone.now()
    cutoff = now - timedelta(hours=3)  # an event stays "upcoming" until a few hours after it starts
    if tab == "past":
        qs = qs.filter(start_at__lt=cutoff).order_by("-start_at")
    elif tab == "saved":
        qs = qs.filter(i_saved=True, start_at__gte=cutoff)
    elif tab == "going":
        qs = qs.filter(i_go=True, start_at__gte=cutoff)
    else:
        tab = "upcoming"
        qs = qs.filter(start_at__gte=cutoff)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(venue__icontains=q))
    if cat in dict(CATEGORIES):
        qs = qs.filter(category=cat)
    qs = qs.order_by("-start_at" if tab == "past" else "start_at")
    page = Paginator(qs, 9).get_page(g.get("page"))
    params = g.copy(); params.pop("page", None)
    return render(request, "events/list.html", {"page": page, "tab": tab, "q": q, "cat": cat, "categories": CATEGORIES, "querystring": params.urlencode()})


@login_required
def event_detail(request, pk):
    e = _event(request.user, pk)
    attendees = list(e.registrations.select_related("user__profile")[:12])
    return render(request, "events/detail.html", {"e": e, "attendees": attendees, "can_edit": _can_edit(request.user, e),
                  "full": e.capacity is not None and e.going >= e.capacity, "past": e.start_at < timezone.now()})


@login_required
@rate_limit("event_new", 10, 3600)
def event_create(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved before you can publish events.")
        return redirect("events:list")
    form = EventForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        e.institution, e.organizer = me.institution, me
        e.is_official = me.role in ("faculty", "admin") or me.is_superuser  # decided server-side, never from the form
        e.save()
        messages.success(request, "Event published.")
        return redirect("events:detail", pk=e.pk)
    return render(request, "events/form.html", {"form": form, "title": "Publish an event"})


@login_required
def event_edit(request, pk):
    e = _event(request.user, pk)
    if not _can_edit(request.user, e):
        raise Http404
    form = EventForm(request.POST or None, request.FILES or None, instance=Event.objects.get(pk=e.pk))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Event updated.")
        return redirect("events:detail", pk=e.pk)
    return render(request, "events/form.html", {"form": form, "title": f"Edit {e.title}", "event": e})


@login_required
@require_POST
def event_delete(request, pk):
    e = _event(request.user, pk)
    if not _can_edit(request.user, e):
        raise Http404
    Event.objects.filter(pk=e.pk).delete()
    messages.info(request, "Event deleted.")
    return redirect("events:list")


@login_required
@require_POST
def event_register(request, pk):
    e = _event(request.user, pk)
    if e.start_at < timezone.now():
        messages.error(request, "This event has already started.")
        return redirect("events:detail", pk=e.pk)
    with transaction.atomic():
        ev = Event.objects.select_for_update().get(pk=e.pk)
        if not Reg.objects.filter(event=ev, user=request.user).exists():
            if ev.capacity is not None and Reg.objects.filter(event=ev).count() >= ev.capacity:
                messages.error(request, "Sorry, this event is full.")
            else:
                Reg.objects.create(event=ev, user=request.user)
                messages.success(request, "You're registered. We'll remind you before it starts.")
    return redirect("events:detail", pk=e.pk)


@login_required
@require_POST
def event_unregister(request, pk):
    e = _event(request.user, pk)
    Reg.objects.filter(event_id=e.pk, user=request.user).delete()
    return redirect("events:detail", pk=e.pk)


@login_required
@require_POST
def event_save(request, pk):
    e = _event(request.user, pk)
    obj, created = EventSave.objects.get_or_create(event_id=e.pk, user=request.user)
    if not created:
        obj.delete()
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/app/") and not nxt.startswith("//") else f"/app/events/{e.pk}/")
