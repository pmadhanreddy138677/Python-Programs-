import datetime

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Event, EventRegistration, EventSave
from apps.institutions.models import Institution
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"
FMT = "%Y-%m-%dT%H:%M"


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


def when(**kw):
    return (timezone.localtime() + datetime.timedelta(**kw)).strftime(FMT)


def mkevent(inst, org, title="Fest", hours=48, **kw):
    return Event.objects.create(institution=inst, organizer=org, title=title, description="d", venue="Hall",
                                start_at=timezone.now() + datetime.timedelta(hours=hours), **kw)


def payload(**kw):
    d = {"title": "Hack Night", "description": "Build things", "category": "technology", "venue": "Lab 1", "start_at": when(days=3), "end_at": "", "capacity": ""}
    d.update(kw)
    return d


def test_official_flag_is_server_side(client, inst):
    stu, fac, adm = mk(inst, "s@x.edu", "Stu"), mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "a@x.edu", "Adm", "admin")
    login(client, stu)
    client.post(reverse("events:create"), payload(title="Student fest", is_official="on"))
    login(client, fac); client.post(reverse("events:create"), payload(title="Guest lecture"))
    login(client, adm); client.post(reverse("events:create"), payload(title="Convocation"))
    flags = {e.title: e.is_official for e in Event.objects.all()}
    assert flags == {"Student fest": False, "Guest lecture": True, "Convocation": True}


def test_event_time_validation(client, inst):
    login(client, mk(inst, "s@x.edu", "Stu"))
    assert client.post(reverse("events:create"), payload(start_at=when(days=-1))).status_code == 200
    assert client.post(reverse("events:create"), payload(start_at=when(days=3), end_at=when(days=2))).status_code == 200
    assert client.post(reverse("events:create"), payload(capacity="0")).status_code == 200
    assert not Event.objects.exists()


def test_register_capacity_unregister_and_past(client, inst):
    o, a, b = mk(inst, "o@x.edu", "Org"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    e = mkevent(inst, o, capacity=1)
    login(client, a); client.post(reverse("events:register", args=[e.pk])); client.post(reverse("events:register", args=[e.pk]))
    login(client, b); client.post(reverse("events:register", args=[e.pk]))
    assert list(EventRegistration.objects.values_list("user_id", flat=True)) == [a.pk]
    assert b"Event is full" in client.get(reverse("events:detail", args=[e.pk])).content
    login(client, a); client.post(reverse("events:unregister", args=[e.pk]))
    assert not EventRegistration.objects.exists()
    past = mkevent(inst, o, title="Old", hours=-5)
    client.post(reverse("events:register", args=[past.pk]))
    assert not EventRegistration.objects.exists()


def test_save_toggle_and_tabs(client, inst):
    o, u = mk(inst, "o@x.edu", "Org"), mk(inst, "u@x.edu", "User")
    e1, e2 = mkevent(inst, o, "Going-Event"), mkevent(inst, o, "Saved-Event")
    login(client, u)
    client.post(reverse("events:register", args=[e1.pk])); client.post(reverse("events:save", args=[e2.pk]))
    assert EventSave.objects.count() == 1
    assert "Going-Event" in client.get(reverse("events:list"), {"tab": "going"}).content.decode()
    h = client.get(reverse("events:list"), {"tab": "saved"}).content.decode()
    assert "Saved-Event" in h and "Going-Event" not in h
    client.post(reverse("events:save", args=[e2.pk]))
    assert not EventSave.objects.exists()


def test_edit_delete_permissions_and_isolation(client, inst):
    o, u, adm = mk(inst, "o@x.edu", "Org"), mk(inst, "u@x.edu", "User"), mk(inst, "a@x.edu", "Adm", "admin")
    e = mkevent(inst, o)
    login(client, u)
    assert client.get(reverse("events:edit", args=[e.pk])).status_code == 404
    assert client.post(reverse("events:delete", args=[e.pk])).status_code == 404
    other = Institution.objects.create(name="Other U", slug="other-u")
    login(client, mk(other, "z@y.edu", "Zed"))
    assert client.get(reverse("events:detail", args=[e.pk])).status_code == 404
    assert client.post(reverse("events:register", args=[e.pk])).status_code == 404
    login(client, adm)
    assert client.post(reverse("events:delete", args=[e.pk])).status_code == 302
    assert not Event.objects.exists()


def test_search_and_category_filters(client, inst):
    o = mk(inst, "o@x.edu", "Org")
    mkevent(inst, o, "Robotics Expo", category="technology"); mkevent(inst, o, "Cricket Cup", category="sports")
    login(client, o)
    h = client.get(reverse("events:list"), {"category": "sports"}).content.decode()
    assert "Cricket Cup" in h and "Robotics Expo" not in h
    assert "Robotics Expo" in client.get(reverse("events:list"), {"q": "robot"}).content.decode()


def test_reminder_command_sends_once(client, inst):
    o, a, b = mk(inst, "o@x.edu", "Org"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    soon, later = mkevent(inst, o, "Soon", hours=5), mkevent(inst, o, "Later", hours=100)
    EventRegistration.objects.create(event=soon, user=a); EventSave.objects.create(event=soon, user=b)
    EventRegistration.objects.create(event=later, user=a)
    call_command("send_event_reminders")
    assert Notification.objects.filter(kind="event").count() == 2
    assert Notification.objects.filter(user=a, title__contains="Soon").exists() and not Notification.objects.filter(title__contains="Later").exists()
    call_command("send_event_reminders")
    assert Notification.objects.filter(kind="event").count() == 2  # not repeated


def test_event_pages_render(client, inst):
    o = mk(inst, "o@x.edu", "Org"); e = mkevent(inst, o)
    login(client, o)
    for url in (reverse("events:list"), reverse("events:list") + "?tab=past", reverse("events:create"), reverse("events:detail", args=[e.pk]), reverse("events:edit", args=[e.pk]), reverse("dashboard:home")):
        assert client.get(url).status_code == 200, url
