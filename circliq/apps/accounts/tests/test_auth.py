import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.tokens import make_token
from apps.institutions.models import Department, Institution, Program

pytestmark = pytest.mark.django_db


@pytest.fixture
def inst():
    # Make the seeded Marwadi record inactive so the test institution is the one used.
    Institution.objects.update(is_active=False)
    i = Institution.objects.create(name="Test University", slug="test-uni")
    d = Department.objects.create(institution=i, name="CSE")
    Program.objects.create(institution=i, department=d, name="B.Tech")
    return i


def payload(inst, **over):
    data = {
        "full_name": "Asha Patel", "email": "asha@test.edu", "account_type": "student",
        "department": Department.objects.get(institution=inst).pk,
        "program": Program.objects.get(institution=inst).pk, "academic_year": "2",
        "password1": "Str0ng-Pass-9871", "password2": "Str0ng-Pass-9871",
    }
    data.update(over)
    return data


def test_registration_creates_unverified_student_and_sends_email(client, inst):
    r = client.post(reverse("accounts:register"), payload(inst))
    assert r.status_code == 302
    u = User.objects.get(email="asha@test.edu")
    assert u.role == "student" and not u.is_email_verified and u.institution == inst
    assert len(mail.outbox) == 1 and "/accounts/verify/" in mail.outbox[0].body


def test_duplicate_email_rejected(client, inst):
    client.post(reverse("accounts:register"), payload(inst))
    r = client.post(reverse("accounts:register"), payload(inst, email="ASHA@test.edu"))
    assert r.status_code == 200 and User.objects.count() == 1


def test_cannot_register_as_admin(client, inst):
    r = client.post(reverse("accounts:register"), payload(inst, account_type="admin"))
    assert r.status_code == 200 and not User.objects.exists()


def test_extra_role_field_is_ignored(client, inst):
    client.post(reverse("accounts:register"), payload(inst, role="admin", is_staff="on", is_superuser="on"))
    u = User.objects.get()
    assert u.role == "student" and not u.is_staff and not u.is_superuser


def test_faculty_needs_approval(client, inst):
    client.post(reverse("accounts:register"), payload(inst, account_type="faculty", email="prof@test.edu", program="", academic_year=""))
    u = User.objects.get(email="prof@test.edu")
    assert u.role == "faculty" and u.is_approved is False


def test_email_domain_rule_enforced(client, inst):
    inst.allowed_email_domains = "test.edu"
    inst.save()
    r = client.post(reverse("accounts:register"), payload(inst, email="x@gmail.com"))
    assert r.status_code == 200 and not User.objects.exists()


def test_cross_institution_department_rejected(client, inst):
    other = Institution.objects.create(name="Other U", slug="other-u")
    foreign = Department.objects.create(institution=other, name="Foreign")
    r = client.post(reverse("accounts:register"), payload(inst, department=foreign.pk))
    assert r.status_code == 200 and not User.objects.exists()


def test_weak_and_mismatched_passwords_rejected(client, inst):
    assert client.post(reverse("accounts:register"), payload(inst, password1="123", password2="123")).status_code == 200
    assert client.post(reverse("accounts:register"), payload(inst, password2="different-9871")).status_code == 200
    assert not User.objects.exists()


def make_user(inst, verified=True):
    return User.objects.create_user("asha@test.edu", "Str0ng-Pass-9871", full_name="Asha Patel",
                                    institution=inst, is_email_verified=verified)


def test_login_blocked_until_verified_then_allowed(client, inst):
    u = make_user(inst, verified=False)
    r = client.post(reverse("accounts:login"), {"username": u.email, "password": "Str0ng-Pass-9871"})
    assert r.status_code == 200 and "_auth_user_id" not in client.session
    assert client.get(reverse("accounts:verify_email", args=[make_token(u)])).status_code == 302
    r = client.post(reverse("accounts:login"), {"username": u.email, "password": "Str0ng-Pass-9871"})
    assert r.status_code == 302 and "_auth_user_id" in client.session


def test_bad_token_rejected(client, inst):
    u = make_user(inst, verified=False)
    client.get(reverse("accounts:verify_email", args=["garbage"]))
    u.refresh_from_db()
    assert not u.is_email_verified


def test_logout_requires_post(client, inst):
    make_user(inst)
    client.login(username="asha@test.edu", password="Str0ng-Pass-9871")
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.post(reverse("accounts:logout")).status_code == 302
    assert "_auth_user_id" not in client.session


def test_dashboard_requires_login_and_greets_by_name(client, inst):
    assert client.get(reverse("dashboard:home")).status_code == 302
    u = make_user(inst)
    client.login(username="asha@test.edu", password="Str0ng-Pass-9871")
    assert client.get(reverse("dashboard:home")).status_code == 302  # new users go to onboarding first
    u.profile.onboarding_complete = True
    u.profile.save()
    r = client.get(reverse("dashboard:home"))
    assert r.status_code == 200 and b"Asha!" in r.content


def test_login_rate_limit(client, inst):
    from django.core.cache import cache
    cache.clear()
    make_user(inst)
    for _ in range(5):
        client.post(reverse("accounts:login"), {"username": "asha@test.edu", "password": "wrong"})
    assert client.post(reverse("accounts:login"), {"username": "asha@test.edu", "password": "Str0ng-Pass-9871"}).status_code == 429


def test_public_pages_render(client, inst):
    for name in ["landing", "accounts:login", "accounts:register", "accounts:password_reset", "accounts:resend_verification"]:
        assert client.get(reverse(name)).status_code == 200, name


def test_password_reset_sends_email(client, inst):
    make_user(inst)
    client.post(reverse("accounts:password_reset"), {"email": "asha@test.edu"})
    assert len(mail.outbox) == 1 and "/accounts/reset/" in mail.outbox[0].body


def test_superuser_is_admin_role():
    u = User.objects.create_superuser("root@x.edu", "pw-12345-abc", full_name="Root")
    assert u.role == "admin" and u.is_staff and u.is_superuser
