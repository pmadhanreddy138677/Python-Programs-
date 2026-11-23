import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.campusadmin.models import AuditLog
from apps.communities.models import Community
from apps.connections.models import Connection
from apps.institutions.models import Institution
from apps.messaging import services as chat
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"
URLS = ["campusadmin:dashboard", "campusadmin:users", "campusadmin:communities", "campusadmin:reports", "campusadmin:audit"]


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name, role="student", approved=True):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True, role=role, is_approved=approved)
    u.profile.onboarding_complete = True
    u.profile.save()
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


def test_only_admins_reach_the_dashboard(client, inst):
    stu, fac, adm = mk(inst, "s@x.edu", "S"), mk(inst, "f@x.edu", "F", "faculty"), mk(inst, "a@x.edu", "A", "admin")
    for name in URLS:
        assert client.get(reverse(name)).status_code == 302                       # anonymous -> login
    for who in (stu, fac):
        login(client, who)
        for name in URLS:
            assert client.get(reverse(name)).status_code == 403, (who.role, name)
        assert b"Campus admin" not in client.get(reverse("dashboard:home")).content   # not even in the sidebar
    login(client, adm)
    for name in URLS:
        assert client.get(reverse(name)).status_code == 200, name
    assert b"Campus admin" in client.get(reverse("dashboard:home")).content


def test_statistics_are_real_and_campus_scoped(client, inst):
    adm = mk(inst, "a@x.edu", "Admin", "admin")
    mk(inst, "s1@x.edu", "S1"); mk(inst, "s2@x.edu", "S2"); mk(inst, "f@x.edu", "F", "faculty"); mk(inst, "p@x.edu", "Pending", "faculty", approved=False)
    Community.objects.create(institution=inst, name="C1", description="d", is_official=True); Community.objects.create(institution=inst, name="C2", description="d")
    other = Institution.objects.create(name="Other U", slug="other-u"); mk(other, "z@y.edu", "Foreign"); Community.objects.create(institution=other, name="Far", description="d")
    from apps.campusadmin.services import stats
    s = stats(inst)
    assert s["total_users"] == 5 and s["students"] == 2 and s["faculty"] == 1 and s["pending_faculty"] == 1
    assert s["communities"] == 2 and s["official_communities"] == 1
    assert sum(d["n"] for d in s["signups"]) == 5 and len(s["signups"]) == 14
    login(client, adm)
    assert b"Faculty awaiting approval" in client.get(reverse("campusadmin:dashboard")).content


def test_private_messages_never_appear_on_any_admin_page(client, inst):
    adm, a, b = mk(inst, "adm@x.edu", "Admin", "admin"), mk(inst, "a@x.edu", "Alice"), mk(inst, "b@x.edu", "Bob")
    Connection.objects.create(requester=a, receiver=b, status="accepted")
    chat.post_message(chat.get_or_create_direct(a, b), a, "TOP-SECRET-MESSAGE-BODY")
    login(client, adm)
    for name in URLS:
        assert b"TOP-SECRET-MESSAGE-BODY" not in client.get(reverse(name)).content, name
    assert b"TOP-SECRET-MESSAGE-BODY" not in client.get(reverse("campusadmin:users"), {"q": "TOP-SECRET"}).content
    assert client.get(f"/{__import__('django').conf.settings.ADMIN_URL}messaging/message/").status_code in (302, 403, 404)


def test_faculty_verification_with_notification_and_audit(client, inst):
    adm, fac = mk(inst, "a@x.edu", "Admin", "admin"), mk(inst, "f@x.edu", "Prof", "faculty", approved=False)
    login(client, adm)
    client.post(reverse("campusadmin:user_action", args=[fac.pk, "approve"]))
    fac.refresh_from_db()
    assert fac.is_approved and Notification.objects.filter(user=fac, title__contains="approved").exists()
    log = AuditLog.objects.get()
    assert log.action == "faculty_approved" and log.actor == adm and log.target == "f@x.edu" and log.institution == inst
    rej = mk(inst, "g@x.edu", "Prof2", "faculty", approved=False)
    client.post(reverse("campusadmin:user_action", args=[rej.pk, "reject"]))
    rej.refresh_from_db()
    assert not rej.is_active and rej.is_restricted and not client.login(username=rej.email, password=PW)


def test_restrict_and_lift_with_audit_trail(client, inst):
    adm, stu = mk(inst, "a@x.edu", "Admin", "admin"), mk(inst, "s@x.edu", "Student")
    login(client, adm)
    client.post(reverse("campusadmin:user_action", args=[stu.pk, "restrict"]), {"reason": "Harassment"})
    stu.refresh_from_db()
    assert not stu.is_active and stu.is_restricted and stu.restriction_reason == "Harassment"
    client.logout(); assert not client.login(username=stu.email, password=PW)
    login(client, adm)
    client.post(reverse("campusadmin:user_action", args=[stu.pk, "unrestrict"]))
    stu.refresh_from_db(); assert stu.is_active and not stu.is_restricted
    assert list(AuditLog.objects.values_list("action", flat=True).order_by("created_at")) == ["account_restricted", "account_unrestricted"]
    assert "Harassment" in AuditLog.objects.get(action="account_restricted").detail


def test_admin_safeguards(client, inst):
    adm, adm2, stu = mk(inst, "a@x.edu", "Admin", "admin"), mk(inst, "a2@x.edu", "Admin2", "admin"), mk(inst, "s@x.edu", "Student")
    login(client, adm)
    client.post(reverse("campusadmin:user_action", args=[adm.pk, "restrict"]))                                   # self
    assert client.post(reverse("campusadmin:user_action", args=[adm2.pk, "restrict"])).status_code == 403        # other admin
    assert client.post(reverse("campusadmin:user_action", args=[stu.pk, "make_superuser"])).status_code == 403   # unknown action
    assert client.post(reverse("campusadmin:user_action", args=[stu.pk, "approve"])).status_code == 403          # approve is faculty-only
    adm.refresh_from_db(); adm2.refresh_from_db(); stu.refresh_from_db()
    assert adm.is_active and adm2.is_active and not stu.is_restricted and not AuditLog.objects.exists()
    assert client.get(reverse("campusadmin:user_action", args=[stu.pk, "restrict"])).status_code == 405          # POST only


def test_cross_campus_users_cannot_be_touched(client, inst):
    adm = mk(inst, "a@x.edu", "Admin", "admin")
    other = Institution.objects.create(name="Other U", slug="other-u"); far = mk(other, "z@y.edu", "Foreign")
    login(client, adm)
    assert client.post(reverse("campusadmin:user_action", args=[far.pk, "restrict"])).status_code == 404
    assert b"Foreign" not in client.get(reverse("campusadmin:users")).content
    far.refresh_from_db(); assert far.is_active
    oc = Community.objects.create(institution=other, name="Far", description="d")
    assert client.post(reverse("campusadmin:official", args=[oc.pk])).status_code == 404


def test_official_toggle_is_audited_and_filters_work(client, inst):
    adm = mk(inst, "a@x.edu", "Admin", "admin")
    mk(inst, "f@x.edu", "Pending Prof", "faculty", approved=False); mk(inst, "s@x.edu", "Plain Student")
    c = Community.objects.create(institution=inst, name="Chess", description="d")
    login(client, adm)
    client.post(reverse("campusadmin:official", args=[c.pk]))
    c.refresh_from_db(); assert c.is_official and AuditLog.objects.get().action == "community_official_on"
    html = client.get(reverse("campusadmin:users"), {"status": "pending"}).content.decode()
    assert "Pending Prof" in html and "Plain Student" not in html
    assert "Plain Student" in client.get(reverse("campusadmin:users"), {"q": "plain"}).content.decode()
    assert "community_official_on" in client.get(reverse("campusadmin:audit")).content.decode()
