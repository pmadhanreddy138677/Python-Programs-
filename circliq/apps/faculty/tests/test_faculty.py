import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.faculty.models import Announcement, FacultyProfile, MentorshipRequest
from apps.institutions.models import Institution
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"


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


def test_faculty_profile_autocreated_and_directory_visibility(client, inst):
    f = mk(inst, "f@x.edu", "Visible Prof", "faculty")
    mk(inst, "p@x.edu", "Pending Prof", "faculty", approved=False)
    other = Institution.objects.create(name="Other U", slug="other-u")
    mk(other, "o@y.edu", "Foreign Prof", "faculty")
    stu = mk(inst, "s@x.edu", "Stu")
    assert FacultyProfile.objects.filter(user=f).exists()
    login(client, stu)
    html = client.get(reverse("faculty:directory")).content.decode()
    assert "Visible Prof" in html and "Pending Prof" not in html and "Foreign Prof" not in html
    assert client.get(reverse("faculty:detail", args=[User.objects.get(full_name="Pending Prof").pk])).status_code == 404
    assert client.get(reverse("faculty:detail", args=[f.pk])).status_code == 200


def test_directory_search_and_mentorship_filter(client, inst):
    a, b = mk(inst, "a@x.edu", "Prof A", "faculty"), mk(inst, "b@x.edu", "Prof B", "faculty")
    a.faculty_profile.expertise = "Machine Learning"; a.faculty_profile.save()
    b.faculty_profile.accepts_mentorship = False; b.faculty_profile.save()
    login(client, mk(inst, "s@x.edu", "Stu"))
    h = client.get(reverse("faculty:directory"), {"q": "machine"}).content.decode()
    assert "Prof A" in h and "Prof B" not in h
    h = client.get(reverse("faculty:directory"), {"mentorship": "1"}).content.decode()
    assert "Prof A" in h and "Prof B" not in h


def test_mentorship_flow_and_permissions(client, inst):
    f, other_f, stu = mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "g@x.edu", "Other Prof", "faculty"), mk(inst, "s@x.edu", "Stu")
    login(client, stu)
    client.post(reverse("faculty:request", args=[f.pk]), {"message": "Please guide my ML project"})
    client.post(reverse("faculty:request", args=[f.pk]), {"message": "again"})  # duplicate pending
    r = MentorshipRequest.objects.get()
    assert Notification.objects.filter(user=f, kind="mentorship").count() == 1
    login(client, other_f)
    assert client.post(reverse("faculty:respond", args=[r.pk, "accept"])).status_code == 404  # not addressed to them
    login(client, stu)
    assert client.post(reverse("faculty:respond", args=[r.pk, "accept"])).status_code == 404
    login(client, f)
    assert b"ML project" in client.get(reverse("faculty:requests")).content
    client.post(reverse("faculty:respond", args=[r.pk, "accept"]))
    r.refresh_from_db()
    assert r.status == "accepted" and Notification.objects.filter(user=stu, kind="mentorship").exists()


def test_mentorship_blocked_when_off_or_not_student(client, inst):
    f, stu = mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "s@x.edu", "Stu")
    f.faculty_profile.accepts_mentorship = False; f.faculty_profile.save()
    login(client, stu)
    assert client.post(reverse("faculty:request", args=[f.pk]), {"message": "hi"}).status_code == 404
    f.faculty_profile.accepts_mentorship = True; f.faculty_profile.save()
    login(client, mk(inst, "g@x.edu", "Prof2", "faculty"))
    assert client.post(reverse("faculty:request", args=[f.pk]), {"message": "hi"}).status_code == 404  # faculty can't request
    assert not MentorshipRequest.objects.exists()


def test_only_faculty_edit_profile(client, inst):
    f, stu = mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "s@x.edu", "Stu")
    login(client, stu)
    assert client.get(reverse("faculty:edit")).status_code == 404
    login(client, f)
    client.post(reverse("faculty:edit"), {"designation": "Professor", "expertise": "AI, Databases", "research_interests": "x", "office_hours": "Mon 3pm"})
    f.faculty_profile.refresh_from_db()
    assert f.faculty_profile.designation == "Professor" and f.faculty_profile.expertise_list() == ["AI", "Databases"]
    assert f.faculty_profile.allow_direct_messages is False  # unchecked box


def test_announcements_permissions_and_fanout(client, inst):
    f, stu, stu2 = mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "s@x.edu", "Stu"), mk(inst, "t@x.edu", "Stu2")
    other = Institution.objects.create(name="Other U", slug="other-u")
    far = mk(other, "o@y.edu", "Far")
    login(client, stu)
    assert client.get(reverse("faculty:announcement_new")).status_code == 404
    assert client.post(reverse("faculty:announcement_new"), {"title": "x", "body": "y"}).status_code == 404
    login(client, f)
    client.post(reverse("faculty:announcement_new"), {"title": "Exam schedule", "body": "Posted", "link": "javascript:alert(1)"})
    assert not Announcement.objects.exists()  # unsafe link rejected
    client.post(reverse("faculty:announcement_new"), {"title": "Exam schedule", "body": "Posted", "link": "https://example.com/s"})
    a = Announcement.objects.get()
    assert Notification.objects.filter(kind="announcement").count() == 2  # stu, stu2 (not author, not other campus)
    assert not Notification.objects.filter(user__in=[f, far]).exists()
    login(client, stu)
    assert b"Exam schedule" in client.get(reverse("faculty:announcements")).content
    assert client.post(reverse("faculty:announcement_delete", args=[a.pk])).status_code == 404
    login(client, f)
    client.post(reverse("faculty:announcement_delete", args=[a.pk]))
    assert not Announcement.objects.exists()


def test_faculty_pages_render(client, inst):
    f, stu = mk(inst, "f@x.edu", "Prof", "faculty"), mk(inst, "s@x.edu", "Stu")
    Announcement.objects.create(institution=inst, author=f, title="T", body="B")
    login(client, f)
    for url in (reverse("faculty:directory"), reverse("faculty:detail", args=[f.pk]), reverse("faculty:edit"), reverse("faculty:requests"),
                reverse("faculty:announcements"), reverse("faculty:announcement_new")):
        assert client.get(url).status_code == 200, url
    login(client, stu)
    assert client.get(reverse("faculty:detail", args=[f.pk])).status_code == 200
