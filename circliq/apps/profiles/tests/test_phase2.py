import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.connections.models import Block, Connection
from apps.institutions.models import Department, Institution
from apps.profiles.models import Interest, Skill

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name, onboarded=True, role="student", discoverable=True, interests=(), goals=()):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True, role=role)
    p = u.profile
    p.onboarding_complete, p.is_discoverable, p.goals = onboarded, discoverable, list(goals)
    p.save()
    for n in interests:
        p.interests.add(Interest.objects.get(name=n))
    return u


def login(client, u):
    assert client.login(username=u.email, password=PW)


def test_profile_autocreated_and_admin_skips_onboarding(inst):
    s = User.objects.create_user("s@x.edu", PW, full_name="S", institution=inst)
    a = User.objects.create_superuser("a@x.edu", PW, full_name="A")
    assert s.profile.onboarding_complete is False and a.profile.onboarding_complete is True


def test_seed_data_present():
    assert Interest.objects.filter(name="Python").exists() and Skill.objects.filter(name="Django").exists()


def test_dashboard_redirects_to_onboarding_and_progress_saved(client, inst):
    u = mk(inst, "n@x.edu", "New One", onboarded=False)
    login(client, u)
    assert client.get(reverse("dashboard:home")).url == reverse("profiles:onboarding", args=[1])
    assert client.get(reverse("profiles:onboarding", args=[3])).status_code == 302  # can't skip ahead
    py = Interest.objects.get(name="Python")
    client.post(reverse("profiles:onboarding", args=[1]), {"bio": "Hello there"})
    client.post(reverse("profiles:onboarding", args=[2]), {"interests": [py.pk]})
    client.post(reverse("profiles:onboarding", args=[3]), {"goals": ["friends", "study"]})
    u.profile.refresh_from_db()
    assert u.profile.bio == "Hello there" and u.profile.goals == ["friends", "study"] and u.profile.onboarding_step == 4
    assert client.get(reverse("profiles:onboarding", args=[4])).status_code == 200  # community step
    assert client.post(reverse("profiles:onboarding", args=[4])).status_code == 302
    assert client.post(reverse("profiles:onboarding", args=[5])).status_code == 302
    u.profile.refresh_from_db()
    assert u.profile.onboarding_complete
    assert client.get(reverse("dashboard:home")).status_code == 200


def test_skip_advances_without_saving(client, inst):
    u = mk(inst, "n@x.edu", "New One", onboarded=False)
    login(client, u)
    client.post(reverse("profiles:onboarding", args=[1]), {"skip": "1", "bio": "should not save"})
    u.profile.refresh_from_db()
    assert u.profile.bio == "" and u.profile.onboarding_step == 2


def test_discover_filters_and_explains(client, inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python", "Anime"])
    mk(inst, "a@x.edu", "Match Person", interests=["Python", "Anime"])
    mk(inst, "h@x.edu", "Hidden Person", discoverable=False, interests=["Python"])
    mk(inst, "f@x.edu", "Faculty Person", role="faculty")
    other = Institution.objects.create(name="Other U", slug="other-u")
    mk(other, "o@y.edu", "Outsider", interests=["Python"])
    login(client, me)
    r = client.get(reverse("profiles:discover"))
    body = r.content.decode()
    assert "Match Person" in body and "You both enjoy Anime and Python." in body
    for hidden in ("Hidden Person", "Faculty Person", "Outsider"):
        assert hidden not in body
    assert "Match Person" not in client.get(reverse("profiles:discover"), {"q": "zzz"}).content.decode()


def test_discover_requires_onboarding(client, inst):
    login(client, mk(inst, "n@x.edu", "N", onboarded=False))
    assert client.get(reverse("profiles:discover")).status_code == 302


def test_connection_flow(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    login(client, a)
    client.post(reverse("connections:send", args=[b.pk]))
    c = Connection.objects.get()
    assert c.status == "pending" and c.requester == a
    client.post(reverse("connections:send", args=[b.pk]))  # duplicate is a no-op
    assert Connection.objects.count() == 1
    client.logout(); login(client, b)
    client.post(reverse("connections:respond", args=[c.pk, "accept"]))
    c.refresh_from_db()
    assert c.status == "accepted"
    assert b"Aaa" in client.get(reverse("connections:list")).content


def test_only_receiver_can_respond_and_no_self_connect(client, inst):
    a, b, evil = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb"), mk(inst, "e@x.edu", "Eve")
    c = Connection.objects.create(requester=a, receiver=b)
    login(client, evil)
    assert client.post(reverse("connections:respond", args=[c.pk, "accept"])).status_code == 404
    assert client.post(reverse("connections:cancel", args=[c.pk])).status_code == 404
    client.logout(); login(client, a)
    assert client.post(reverse("connections:respond", args=[c.pk, "accept"])).status_code == 404  # requester can't self-accept
    assert client.post(reverse("connections:send", args=[a.pk])).status_code == 404
    c.refresh_from_db()
    assert c.status == "pending"


def test_cannot_connect_across_institutions_or_to_hidden(client, inst):
    me = mk(inst, "me@x.edu", "Me")
    other = Institution.objects.create(name="Other U", slug="other-u")
    out = mk(other, "o@y.edu", "Outsider")
    hid = mk(inst, "h@x.edu", "Hidden", discoverable=False)
    login(client, me)
    assert client.post(reverse("connections:send", args=[out.pk])).status_code == 404
    client.post(reverse("connections:send", args=[hid.pk]))
    assert not Connection.objects.exists()
    assert client.get(reverse("profiles:detail", args=[out.pk])).status_code == 404
    assert client.get(reverse("profiles:detail", args=[hid.pk])).status_code == 404


def test_mutual_request_auto_accepts(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    Connection.objects.create(requester=b, receiver=a)
    login(client, a)
    client.post(reverse("connections:send", args=[b.pk]))
    assert Connection.objects.get().status == "accepted"


def test_block_removes_connection_and_hides_both_ways(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa", interests=["Python"]), mk(inst, "b@x.edu", "Bbb", interests=["Python"])
    Connection.objects.create(requester=a, receiver=b, status="accepted")
    login(client, a)
    client.post(reverse("connections:block", args=[b.pk]))
    assert not Connection.objects.exists() and Block.objects.count() == 1
    assert reverse("profiles:detail", args=[b.pk]) not in client.get(reverse("profiles:discover")).content.decode()
    assert client.get(reverse("profiles:detail", args=[b.pk])).status_code == 404
    client.logout(); login(client, b)
    assert reverse("profiles:detail", args=[a.pk]) not in client.get(reverse("profiles:discover")).content.decode()
    assert client.post(reverse("connections:send", args=[a.pk])).status_code == 404
    assert client.get(reverse("profiles:detail", args=[a.pk])).status_code == 404


def test_edit_profile_and_discoverability(client, inst):
    me = mk(inst, "me@x.edu", "Me")
    dept = Department.objects.create(institution=inst, name="CSE")
    py = Interest.objects.get(name="Python")
    login(client, me)
    r = client.post(reverse("profiles:edit"), {"full_name": "Me Renamed", "bio": "Hi", "department": dept.pk,
                                               "academic_year": "3", "interests": [py.pk], "goals": ["projects"]})
    assert r.status_code == 302
    me.refresh_from_db()
    assert me.full_name == "Me Renamed" and me.academic_year == 3 and me.profile.is_discoverable is False  # unchecked box
    assert client.get(reverse("profiles:me")).status_code == 302


def test_edit_rejects_foreign_department(client, inst):
    me = mk(inst, "me@x.edu", "Me")
    foreign = Department.objects.create(institution=Institution.objects.create(name="O", slug="o"), name="X")
    login(client, me)
    r = client.post(reverse("profiles:edit"), {"full_name": "Me", "department": foreign.pk})
    assert r.status_code == 200


def test_pages_render_for_logged_in_user(client, inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python"])
    other = mk(inst, "o@x.edu", "Oth", interests=["Python"])
    login(client, me)
    for url in (reverse("dashboard:home"), reverse("profiles:discover"), reverse("connections:list"),
                reverse("profiles:edit"), reverse("profiles:detail", args=[other.pk]), reverse("profiles:detail", args=[me.pk])):
        assert client.get(url).status_code == 200, url
