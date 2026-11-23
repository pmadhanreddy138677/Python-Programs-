import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.connections.models import Block, Connection
from apps.institutions.models import Institution
from apps.messaging import services as s
from apps.messaging.models import Conversation, Message
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name, role="student"):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True, role=role)
    u.profile.onboarding_complete = True
    u.profile.save()
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


def connect(a, b):
    Connection.objects.create(requester=a, receiver=b, status="accepted")


def test_dm_requires_connection_unless_faculty_allows(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    prof, closed = mk(inst, "p@x.edu", "Prof", "faculty"), mk(inst, "c@x.edu", "Closed", "faculty")
    closed.faculty_profile.allow_direct_messages = False
    closed.faculty_profile.save()
    login(client, a)
    client.post(reverse("messaging:start", args=[b.pk]))
    assert not Conversation.objects.exists()  # stranger student
    client.post(reverse("messaging:start", args=[closed.pk]))
    assert not Conversation.objects.exists()  # faculty with DMs off
    assert client.post(reverse("messaging:start", args=[prof.pk])).status_code == 302
    assert Conversation.objects.count() == 1
    connect(a, b)
    client.post(reverse("messaging:start", args=[b.pk]))
    assert Conversation.objects.count() == 2


def test_direct_conversation_is_deduplicated(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    connect(a, b)
    login(client, a); client.post(reverse("messaging:start", args=[b.pk]))
    login(client, b); client.post(reverse("messaging:start", args=[a.pk]))
    assert Conversation.objects.count() == 1


def _chat(client, a, b):
    connect(a, b)
    login(client, a)
    client.post(reverse("messaging:start", args=[b.pk]))
    return Conversation.objects.get()


def test_send_store_unread_and_mark_read(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    r = client.post(reverse("messaging:send", args=[c.pk]), {"body": "hello there"})
    assert r.status_code == 200 and r.json()["message"]["body"] == "hello there"
    assert Message.objects.get().sender == a
    login(client, b)
    assert s.total_unread(b) == 1 and s.total_unread(a) == 0
    assert b"hello there" in client.get(reverse("messaging:chat", args=[c.pk])).content
    assert s.total_unread(b) == 0  # opening the chat marks it read


def test_validation_empty_and_too_long(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    assert client.post(reverse("messaging:send", args=[c.pk]), {"body": "   "}).status_code == 400
    assert client.post(reverse("messaging:send", args=[c.pk]), {"body": "x" * 2001}).status_code == 400
    assert not Message.objects.exists()


def test_non_participants_and_other_institutions_cannot_access(client, inst):
    a, b, outsider = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb"), mk(inst, "o@x.edu", "Outsider")
    c = _chat(client, a, b)
    client.post(reverse("messaging:send", args=[c.pk]), {"body": "private stuff"})
    other = Institution.objects.create(name="Other U", slug="other-u")
    for who in (outsider, mk(other, "z@y.edu", "Zed")):
        login(client, who)
        assert client.get(reverse("messaging:chat", args=[c.pk])).status_code == 404
        assert client.post(reverse("messaging:send", args=[c.pk]), {"body": "intrude"}).status_code == 404
        assert client.get(reverse("messaging:poll", args=[c.pk])).status_code == 404
        assert client.post(reverse("messaging:read", args=[c.pk])).status_code == 404
        assert b"private stuff" not in client.get(reverse("messaging:inbox")).content
    assert Message.objects.count() == 1


def test_blocking_is_enforced_on_send_and_start(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    client.post(reverse("messaging:send", args=[c.pk]), {"body": "before"})
    Block.objects.create(blocker=b, blocked=a)
    r = client.post(reverse("messaging:send", args=[c.pk]), {"body": "after block"})
    assert r.status_code == 403 and Message.objects.count() == 1
    login(client, b)
    assert client.post(reverse("messaging:send", args=[c.pk]), {"body": "me too"}).status_code == 403
    assert b"can&#x27;t send messages" in client.get(reverse("messaging:chat", args=[c.pk])).content or b"can't send messages" in client.get(reverse("messaging:chat", args=[c.pk])).content


def test_group_rules_send_and_leave(client, inst):
    a, b, c, d, stranger = (mk(inst, f"{n}@x.edu", n.upper()) for n in "abcds")
    for x in (b, c, d):
        connect(a, x)
    login(client, a)
    assert client.post(reverse("messaging:new_group"), {"name": "G", "members": [b.pk]}).status_code == 200  # needs 2+
    assert client.post(reverse("messaging:new_group"), {"name": "G", "members": [b.pk, stranger.pk]}).status_code == 200  # strangers rejected
    assert not Conversation.objects.exists()
    r = client.post(reverse("messaging:new_group"), {"name": "Study", "members": [b.pk, c.pk]})
    g = Conversation.objects.get()
    assert r.status_code == 302 and g.kind == "group" and g.participants.count() == 3
    client.post(reverse("messaging:send", args=[g.pk]), {"body": "hi team"})
    assert s.total_unread(b) == 1 and s.total_unread(c) == 1 and s.total_unread(d) == 0
    login(client, d)
    assert client.get(reverse("messaging:chat", args=[g.pk])).status_code == 404
    login(client, c)
    client.post(reverse("messaging:leave", args=[g.pk]))
    assert g.participants.count() == 2
    assert client.get(reverse("messaging:chat", args=[g.pk])).status_code == 404


def test_message_notifications_coalesce(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    for t in ("one", "two", "three"):
        client.post(reverse("messaging:send", args=[c.pk]), {"body": t})
    n = Notification.objects.filter(user=b, kind="message")
    assert n.count() == 1 and n.get().body == "three" and not Notification.objects.filter(user=a).exists()


def test_messages_are_escaped_and_poll_returns_new(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    first = client.post(reverse("messaging:send", args=[c.pk]), {"body": "<img src=x onerror=alert(1)>"}).json()["message"]["id"]
    client.post(reverse("messaging:send", args=[c.pk]), {"body": "second"})
    html = client.get(reverse("messaging:chat", args=[c.pk])).content.decode()
    assert "<img src=x" not in html and "&lt;img src=x" in html
    got = client.get(reverse("messaging:poll", args=[c.pk]), {"after": first}).json()["messages"]
    assert [m["body"] for m in got] == ["second"]


def test_inbox_pages_render(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    c = _chat(client, a, b)
    client.post(reverse("messaging:send", args=[c.pk]), {"body": "hi"})
    for url in (reverse("messaging:inbox"), reverse("messaging:chat", args=[c.pk]), reverse("messaging:new_group")):
        assert client.get(url).status_code == 200, url
