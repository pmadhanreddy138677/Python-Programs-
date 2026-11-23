import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import User
from apps.connections.models import Block, Connection
from apps.institutions.models import Institution
from apps.messaging import services as s
from apps.messaging.consumers import ChatConsumer
from apps.messaging.models import Message
from apps.notifications.consumers import NotificationConsumer
from apps.notifications.services import notify

PW = "Str0ng-Pass-9871"
pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


@database_sync_to_async
def setup():
    Institution.objects.update(is_active=False)
    inst = Institution.objects.create(name="WS U", slug="ws-u")
    a = User.objects.create_user("a@w.edu", PW, full_name="Aaa", institution=inst, is_email_verified=True)
    b = User.objects.create_user("b@w.edu", PW, full_name="Bbb", institution=inst, is_email_verified=True)
    out = User.objects.create_user("o@w.edu", PW, full_name="Out", institution=inst, is_email_verified=True)
    Connection.objects.create(requester=a, receiver=b, status="accepted")
    conv = s.get_or_create_direct(a, b)
    return a, b, out, conv


def comm(user, conv_id):
    c = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv_id}/")
    c.scope["user"] = user
    c.scope["url_route"] = {"kwargs": {"conv_id": str(conv_id)}}
    return c


async def test_message_roundtrip_is_delivered_and_stored():
    a, b, out, conv = await setup()
    ca, cb = comm(a, conv.pk), comm(b, conv.pk)
    assert (await ca.connect())[0] and (await cb.connect())[0]
    await ca.send_json_to({"type": "message", "body": "hello over websocket"})
    for c in (ca, cb):
        got = await c.receive_json_from()
        assert got["type"] == "message" and got["message"]["body"] == "hello over websocket" and got["message"]["sender_id"] == a.pk
    assert await database_sync_to_async(Message.objects.count)() == 1
    await ca.disconnect(); await cb.disconnect()


async def test_non_participant_and_anonymous_are_rejected():
    a, b, out, conv = await setup()
    ok, code = await comm(out, conv.pk).connect()
    assert ok is False and code == 4403
    ok, code = await comm(AnonymousUser(), conv.pk).connect()
    assert ok is False and code == 4401


async def test_blocked_user_cannot_send_over_websocket():
    a, b, out, conv = await setup()
    await database_sync_to_async(Block.objects.create)(blocker=b, blocked=a)
    ca = comm(a, conv.pk)
    await ca.connect()
    await ca.send_json_to({"type": "message", "body": "sneaky"})
    got = await ca.receive_json_from()
    assert got["type"] == "error"
    assert await database_sync_to_async(Message.objects.count)() == 0
    await ca.disconnect()


async def test_empty_message_returns_error_and_typing_is_relayed():
    a, b, out, conv = await setup()
    ca, cb = comm(a, conv.pk), comm(b, conv.pk)
    await ca.connect(); await cb.connect()
    await ca.send_json_to({"type": "message", "body": "   "})
    assert (await ca.receive_json_from())["type"] == "error"
    await ca.send_json_to({"type": "typing"})
    got = await cb.receive_json_from()
    assert got == {"type": "typing", "name": "Aaa"}
    assert await ca.receive_nothing()  # you don't see your own typing indicator
    await ca.disconnect(); await cb.disconnect()


async def test_live_notification_push():
    a, b, out, conv = await setup()
    c = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    c.scope["user"] = b
    assert (await c.connect())[0]
    await database_sync_to_async(notify)(b, "reply", "Someone replied", "hi", "/app/", actor=a)
    got = await c.receive_json_from()
    assert got["type"] == "notification" and got["title"] == "Someone replied" and got["unread"] == 1
    await c.disconnect()
    anon = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
    anon.scope["user"] = AnonymousUser()
    assert (await anon.connect())[0] is False
