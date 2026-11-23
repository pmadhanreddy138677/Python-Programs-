from django.db.models import Q

from .models import Block, Connection


def blocked_ids(user):
    """IDs of users the given user blocked OR who blocked them (hidden both ways)."""
    ids = set()
    for a, b in Block.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id"):
        ids.update((a, b))
    ids.discard(user.id)
    return ids


def accepted_q(user):
    return Q(status="accepted") & (Q(requester=user) | Q(receiver=user))


def connection_count(user):
    return Connection.objects.filter(accepted_q(user)).count()


def relations_for(me, user_ids):
    """Map other_user_id -> (state, connection_id). state: connected | sent | received."""
    out = {}
    qs = Connection.objects.filter(
        Q(requester=me, receiver_id__in=user_ids) | Q(receiver=me, requester_id__in=user_ids)).select_related("requester", "receiver")
    for c in qs:
        if c.status == "accepted":
            out[c.other(me).id] = ("connected", c.id)
        elif c.requester_id == me.id:
            out[c.receiver_id] = ("sent", c.id)
        else:
            out[c.requester_id] = ("received", c.id)
    return out


def relation(me, other):
    if me.id == other.id:
        return "self", None
    return relations_for(me, [other.id]).get(other.id, ("none", None))
