import json

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.circles.models import Circle, CircleMembership
from apps.communities.models import Community, CommunityMembership
from apps.connections.models import Connection
from apps.discussions.models import Post
from apps.institutions.models import Institution
from apps.messaging import services as chat
from apps.messaging.models import Message
from apps.profiles.models import Interest

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


def test_data_export_contains_own_data_only(client, inst):
    me, other = mk(inst, "me@x.edu", "Me"), mk(inst, "o@x.edu", "Other Person")
    me.profile.bio, me.profile.study_subjects = "My bio", "DBMS"; me.profile.save()
    me.profile.interests.add(Interest.objects.get(name="Python"))
    comm = Community.objects.create(institution=inst, name="C", description="d", created_by=me)
    CommunityMembership.objects.create(community=comm, user=me, role="owner")
    Post.objects.create(community=comm, author=me, body="my own post"); Post.objects.create(community=comm, author=other, body="someone elses post")
    Connection.objects.create(requester=me, receiver=other, status="accepted")
    chat.post_message(chat.get_or_create_direct(me, other), me, "PRIVATE-CHAT-TEXT")
    client.logout(); assert client.get(reverse("accounts:export")).status_code == 302
    login(client, me)
    r = client.get(reverse("accounts:export"))
    data = json.loads(r.content)
    assert "attachment" in r["Content-Disposition"] and data["account"]["email"] == "me@x.edu"
    assert data["profile"]["bio"] == "My bio" and "Python" in data["profile"]["interests"] and data["connection_count"] == 1
    assert [p["body"] for p in data["posts"]] == ["my own post"]
    text = r.content.decode()
    assert "PRIVATE-CHAT-TEXT" not in text and "someone elses post" not in text and "Other Person" not in text and "o@x.edu" not in text


def test_deactivate_requires_password_hides_and_is_reversible(client, inst):
    me, other = mk(inst, "me@x.edu", "Me Visible", ), mk(inst, "o@x.edu", "Other")
    login(client, me)
    client.post(reverse("accounts:deactivate"), {"password": "wrong"})
    me.refresh_from_db(); assert me.is_active
    r = client.post(reverse("accounts:deactivate"), {"password": PW})
    me.refresh_from_db()
    assert r.status_code == 302 and not me.is_active and me.deactivated_at and "_auth_user_id" not in client.session
    assert not client.login(username=me.email, password=PW)                       # can't log in while deactivated
    login(client, other)
    assert "Me Visible" not in client.get(reverse("profiles:discover")).content.decode()
    client.logout()
    client.post(reverse("accounts:reactivate"), {"email": me.email, "password": "wrong"})
    me.refresh_from_db(); assert not me.is_active
    client.post(reverse("accounts:reactivate"), {"email": me.email, "password": PW})
    me.refresh_from_db()
    assert me.is_active and me.deactivated_at is None and client.login(username=me.email, password=PW)


def test_admin_restricted_account_cannot_self_reactivate(client, inst):
    u = mk(inst, "u@x.edu", "U")
    u.is_active, u.is_restricted, u.deactivated_at = False, True, None
    u.save()
    client.post(reverse("accounts:reactivate"), {"email": u.email, "password": PW})
    u.refresh_from_db(); assert not u.is_active
    u.deactivated_at = __import__("django").utils.timezone.now(); u.save()          # even if it also looks self-deactivated
    client.post(reverse("accounts:reactivate"), {"email": u.email, "password": PW})
    u.refresh_from_db(); assert not u.is_active


def test_delete_needs_password_and_confirmation_then_removes_everything(client, inst):
    me, other = mk(inst, "me@x.edu", "Me"), mk(inst, "o@x.edu", "Other")
    comm = Community.objects.create(institution=inst, name="C", description="d", created_by=other)
    CommunityMembership.objects.create(community=comm, user=other, role="owner"); CommunityMembership.objects.create(community=comm, user=me)
    Post.objects.create(community=comm, author=me, body="mine"); Post.objects.create(community=comm, author=other, body="theirs")
    conv = chat.get_or_create_direct(me, other) if Connection.objects.create(requester=me, receiver=other, status="accepted") else None
    chat.post_message(conv, me, "bye")
    login(client, me)
    client.post(reverse("accounts:delete"), {"password": PW, "confirm": "delete"})        # wrong confirmation word
    client.post(reverse("accounts:delete"), {"password": "nope", "confirm": "DELETE"})
    assert User.objects.filter(pk=me.pk).exists()
    r = client.post(reverse("accounts:delete"), {"password": PW, "confirm": "DELETE"})
    assert r.status_code == 302 and not User.objects.filter(pk=me.pk).exists() and "_auth_user_id" not in client.session
    assert list(Post.objects.values_list("body", flat=True)) == ["theirs"]                  # others' content untouched
    assert Community.objects.filter(pk=comm.pk).exists() and not Message.objects.filter(body="bye").exists()


def test_delete_blocked_while_others_depend_on_you(client, inst):
    me, other = mk(inst, "me@x.edu", "Me"), mk(inst, "o@x.edu", "Other")
    c = Circle.objects.create(institution=inst, name="Study Crew", purpose="p", created_by=me)
    CircleMembership.objects.create(circle=c, user=me, role="owner"); CircleMembership.objects.create(circle=c, user=other)
    login(client, me)
    r = client.post(reverse("accounts:delete"), {"password": PW, "confirm": "DELETE"}, follow=True)
    assert User.objects.filter(pk=me.pk).exists() and "Study Crew" in r.content.decode()
    CircleMembership.objects.filter(user=other).delete()                                    # nobody depends on it any more
    client.post(reverse("accounts:delete"), {"password": PW, "confirm": "DELETE"})
    assert not User.objects.filter(pk=me.pk).exists()


def test_admins_cannot_self_delete_or_deactivate(client, inst):
    adm = mk(inst, "a@x.edu", "Admin", "admin")
    login(client, adm)
    client.post(reverse("accounts:delete"), {"password": PW, "confirm": "DELETE"})
    assert User.objects.filter(pk=adm.pk).exists()
    assert b"Delete account permanently" not in client.get(reverse("accounts:settings")).content


def test_settings_page_renders(client, inst):
    login(client, mk(inst, "me@x.edu", "Me"))
    html = client.get(reverse("accounts:settings")).content.decode()
    assert "Download my data" in html and "Deactivate account" in html and "Delete account permanently" in html
