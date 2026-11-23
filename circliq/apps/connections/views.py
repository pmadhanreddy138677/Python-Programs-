from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.notifications.services import notify
from .models import Block, Connection
from .services import blocked_ids, relation

User = get_user_model()


def _back(request, fallback="connections:list"):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(fallback)


def _visible_user_or_404(me, pk):
    """Same institution, active, not self, not blocked either way. Anything else is a 404."""
    other = get_object_or_404(User, pk=pk, institution_id=me.institution_id, is_active=True)
    if other.id == me.id or other.id in blocked_ids(me):
        from django.http import Http404
        raise Http404
    return other


@login_required
def connection_list(request):
    me = request.user
    tab = request.GET.get("tab", "connected")
    base = Connection.objects.select_related("requester__profile", "receiver__profile", "requester__department", "receiver__department")
    if tab == "received":
        rows = [(c, c.requester) for c in base.filter(receiver=me, status="pending")]
    elif tab == "sent":
        rows = [(c, c.receiver) for c in base.filter(requester=me, status="pending")]
    elif tab == "blocked":
        rows = [(None, b.blocked) for b in Block.objects.filter(blocker=me).select_related("blocked__profile")]
    else:
        tab = "connected"
        rows = [(c, c.other(me)) for c in base.filter(Q(requester=me) | Q(receiver=me), status="accepted")]
    counts = {
        "connected": Connection.objects.filter(Q(requester=me) | Q(receiver=me), status="accepted").count(),
        "received": Connection.objects.filter(receiver=me, status="pending").count(),
        "sent": Connection.objects.filter(requester=me, status="pending").count(),
        "blocked": Block.objects.filter(blocker=me).count(),
    }
    return render(request, "connections/list.html", {"rows": rows, "tab": tab, "counts": counts})


@login_required
@require_POST
@rate_limit("connect", 40, 86400)
def send_request(request, pk):
    me, other = request.user, None
    other = _visible_user_or_404(me, pk)
    state, conn = relation(me, other)
    if state == "received":  # they already asked us: connecting back accepts
        Connection.objects.filter(pk=conn).update(status="accepted", responded_at=timezone.now())
        messages.success(request, f"You're now connected with {other.full_name}.")
        notify(other, "connection_accepted", f"{me.full_name} accepted your connection", url=f"/app/people/{me.pk}/", actor=me)
    elif state == "none":
        if not other.profile.is_discoverable:
            messages.error(request, "This person isn't accepting new connections right now.")
        else:
            Connection.objects.create(requester=me, receiver=other)
            notify(other, "connection_request", f"{me.full_name} wants to connect", url="/app/connections/?tab=received", actor=me, ref=f"conn:{me.pk}")
            messages.success(request, f"Connection request sent to {other.full_name}.")
    return _back(request, "profiles:discover")


@login_required
@require_POST
def respond(request, pk, action):
    conn = get_object_or_404(Connection, pk=pk, receiver=request.user, status="pending")  # only the receiver
    if action == "accept":
        conn.status, conn.responded_at = "accepted", timezone.now()
        conn.save(update_fields=["status", "responded_at"])
        messages.success(request, f"You're now connected with {conn.requester.full_name}.")
        notify(conn.requester, "connection_accepted", f"{request.user.full_name} accepted your connection", url=f"/app/people/{request.user.pk}/", actor=request.user)
    elif action == "decline":
        conn.delete()
        messages.info(request, "Request declined.")
    else:
        from django.http import Http404
        raise Http404
    return _back(request)


@login_required
@require_POST
def cancel_or_remove(request, pk):
    """Requester cancels a pending request, or either party removes an accepted connection."""
    conn = get_object_or_404(Connection, Q(requester=request.user) | Q(receiver=request.user), pk=pk)
    if conn.status == "pending" and conn.requester_id != request.user.id:
        from django.http import Http404
        raise Http404
    conn.delete()
    messages.info(request, "Done.")
    return _back(request)


@login_required
@require_POST
def block(request, pk):
    other = _visible_user_or_404(request.user, pk)
    Block.objects.get_or_create(blocker=request.user, blocked=other)
    Connection.objects.filter(Q(requester=request.user, receiver=other) | Q(requester=other, receiver=request.user)).delete()
    messages.info(request, f"{other.full_name} is blocked. You won't see each other on Circliq.")
    return redirect("profiles:discover")


@login_required
@require_POST
def unblock(request, pk):
    Block.objects.filter(blocker=request.user, blocked_id=pk).delete()
    messages.info(request, "User unblocked.")
    return redirect("connections:list")
