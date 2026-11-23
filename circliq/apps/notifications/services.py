import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Notification

log = logging.getLogger(__name__)


def _safe_url(url):
    return url if url.startswith("/app/") and not url.startswith("//") else ""


def unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()


def _push(n):
    """Tell the user's open pages about it. Never lets a channel-layer problem break the request."""
    try:
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(f"user_{n.user_id}", {
                "type": "notify.event", "id": n.pk, "title": n.title, "body": n.body,
                "url": f"/app/notifications/open/{n.pk}/", "unread": unread_count(n.user)})
    except Exception:  # pragma: no cover
        log.warning("notification push failed", exc_info=True)


def notify(user, kind, title, body="", url="", actor=None, ref=""):
    """Create (or refresh) a notification. Skips self-notifications."""
    if actor is not None and actor.pk == user.pk:
        return None
    url = _safe_url(url)
    if ref:
        existing = Notification.objects.filter(user=user, kind=kind, ref=ref, is_read=False).first()
        if existing:
            existing.title, existing.body, existing.created_at = title[:160], body[:300], timezone.now()
            existing.save(update_fields=["title", "body", "created_at"])
            _push(existing)
            return existing
    n = Notification.objects.create(user=user, actor=actor, kind=kind, title=title[:160], body=body[:300], url=url, ref=ref)
    _push(n)
    return n


def notify_many(users, kind, title, body="", url="", actor=None):
    users = [u for u in users if actor is None or u.pk != actor.pk]
    url = _safe_url(url)
    rows = Notification.objects.bulk_create([Notification(user=u, actor=actor, kind=kind, title=title[:160], body=body[:300], url=url) for u in users])
    for n in rows:
        _push(n)  # _push already logs and swallows channel-layer failures
    return rows
