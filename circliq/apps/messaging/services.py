import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.connections.models import Connection
from apps.connections.services import blocked_ids
from .models import Conversation, ConversationParticipant as CP, Message

User = get_user_model()


def are_connected(a, b):
    return Connection.objects.filter(status="accepted").filter(
        Q(requester=a, receiver=b) | Q(requester=b, receiver=a)).exists()


def can_message(me, other):
    """Same campus, not blocked, and either connected or a faculty member who accepts direct messages."""
    if me.pk == other.pk or not other.is_active or me.institution_id != other.institution_id:
        return False
    if other.pk in blocked_ids(me):
        return False
    if are_connected(me, other):
        return True
    fac = getattr(other, "faculty_profile", None)
    return other.role == "faculty" and other.is_approved and bool(fac is None or fac.allow_direct_messages)


def direct_key(a, b):
    lo, hi = sorted((a.pk, b.pk))
    return f"{lo}-{hi}"


def get_or_create_direct(me, other):
    with transaction.atomic():
        conv = Conversation.objects.filter(direct_key=direct_key(me, other)).first()
        if conv:
            return conv
        conv = Conversation.objects.create(institution=me.institution, kind="direct", direct_key=direct_key(me, other), created_by=me)
        CP.objects.bulk_create([CP(conversation=conv, user=me), CP(conversation=conv, user=other)])
        return conv


def create_group(me, name, others):
    with transaction.atomic():
        conv = Conversation.objects.create(institution=me.institution, kind="group", name=name[:80], created_by=me)
        CP.objects.bulk_create([CP(conversation=conv, user=u) for u in [me, *others]])
        return conv


def participant(user, conv):
    return CP.objects.filter(conversation=conv, user=user).first()


def other_party(conv, me):
    if conv.kind != "direct":
        return None
    p = conv.participants.exclude(user=me).select_related("user__profile").first()
    return p.user if p else None


def direct_blocked(conv, me):
    """True if either side of a 1:1 chat has blocked the other (blocking is enforced on every send)."""
    if conv.kind != "direct":
        return False
    other = other_party(conv, me)
    return other is None or other.pk in blocked_ids(me)


def conversations_for(user):
    sub = (Message.objects.filter(conversation_id=OuterRef("conversation_id"), created_at__gt=OuterRef("last_read_at"))
           .exclude(sender_id=OuterRef("user_id")).values("conversation_id").annotate(c=Count("pk")).values("c"))
    last = Message.objects.filter(conversation_id=OuterRef("conversation_id")).order_by("-created_at")
    return (CP.objects.filter(user=user).select_related("conversation")
            .annotate(unread=Coalesce(Subquery(sub), 0), last_body=Subquery(last.values("body")[:1]),
                      last_sender=Subquery(last.values("sender__full_name")[:1]))
            .order_by("-conversation__last_message_at"))


def total_unread(user):
    """Single aggregate query. 'filter' keeps both conditions on the same participant row."""
    return (Message.objects.filter(conversation__participants__user=user, created_at__gt=F("conversation__participants__last_read_at"))
            .exclude(sender=user).count())


def title_for(conv, me):
    if conv.kind == "group":
        return conv.name or "Group chat"
    o = other_party(conv, me)
    return o.full_name if o else "Deleted user"


def serialize(msg):
    return {"id": msg.pk, "sender_id": msg.sender_id, "sender": msg.sender.full_name, "body": msg.body,
            "created_at": msg.created_at.isoformat(), "conversation": msg.conversation_id}


def mark_read(conv, user):
    CP.objects.filter(conversation=conv, user=user).update(last_read_at=timezone.now())


def broadcast(conv_id, payload):
    try:
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(f"chat_{conv_id}", payload)
    except Exception:  # pragma: no cover  (a layer outage must not lose the saved message)
        logging.getLogger(__name__).warning("chat broadcast failed", exc_info=True)


def post_message(conv, sender, body):
    """The single path for sending: used by the WebSocket consumer and the HTTP fallback."""
    body = (body or "").strip()
    if not body:
        raise ValidationError("Message is empty.")
    from apps.core.ratelimit import hit
    if not hit(f"rl:msg:{sender.pk}", 60, 60):
        raise ValidationError("You're sending messages too quickly. Please wait a moment.")
    if len(body) > settings.CHAT_MAX_LENGTH:
        raise ValidationError(f"Messages are limited to {settings.CHAT_MAX_LENGTH} characters.")
    if conv.institution_id != sender.institution_id or not participant(sender, conv):
        raise PermissionDenied
    if direct_blocked(conv, sender):
        raise PermissionDenied("You can't message this person.")
    with transaction.atomic():
        msg = Message.objects.create(conversation=conv, sender=sender, body=body)
        Conversation.objects.filter(pk=conv.pk).update(last_message_at=msg.created_at)
        CP.objects.filter(conversation=conv, user=sender).update(last_read_at=msg.created_at)
    broadcast(conv.pk, {"type": "chat.message", "message": serialize(msg)})
    from apps.notifications.services import notify
    title = f"New message from {sender.full_name}" if conv.kind == "direct" else f"{sender.full_name} in {conv.name or 'group chat'}"
    for p in conv.participants.exclude(user=sender).select_related("user"):
        notify(p.user, "message", title, body[:120], f"/app/messages/{conv.pk}/", actor=sender, ref=f"conv:{conv.pk}")
    return msg


def connections_of(user):
    ids = set()
    for c in Connection.objects.filter(Q(requester=user) | Q(receiver=user), status="accepted"):
        ids.add(c.other(user).pk)
    ids -= blocked_ids(user)
    return User.objects.filter(pk__in=ids, is_active=True, institution_id=user.institution_id).select_related("profile").order_by("full_name")
