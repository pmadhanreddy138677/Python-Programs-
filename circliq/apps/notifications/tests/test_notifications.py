import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.circles.models import Circle, CircleMembership as CM
from apps.communities.models import Community, CommunityMembership as M
from apps.connections.models import Connection
from apps.discussions.models import Post
from apps.institutions.models import Institution
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.projects.models import Project, ProjectMembership as PM

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True)
    u.profile.onboarding_complete = True
    u.profile.discoverable = True
    u.profile.save()
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


def test_connection_request_and_accept_notify(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    login(client, a); client.post(reverse("connections:send", args=[b.pk]))
    n = Notification.objects.get(user=b)
    assert n.kind == "connection_request" and "Aaa" in n.title and not n.is_read
    conn = Connection.objects.get()
    login(client, b); client.post(reverse("connections:respond", args=[conn.pk, "accept"]))
    assert Notification.objects.filter(user=a, kind="connection_accepted").exists()


def test_reply_and_project_and_circle_and_community_notifications(client, inst):
    owner, other = mk(inst, "o@x.edu", "Owner"), mk(inst, "t@x.edu", "Other")
    comm = Community.objects.create(institution=inst, name="C", description="d", created_by=owner)
    M.objects.create(community=comm, user=owner, role="owner"); M.objects.create(community=comm, user=other)
    post = Post.objects.create(community=comm, author=owner, body="hello", title="My post")
    login(client, other)
    client.post(reverse("discussions:comment", args=[post.pk]), {"body": "nice one"})
    assert Notification.objects.filter(user=owner, kind="reply").exists()
    client.post(reverse("discussions:comment", args=[post.pk]), {"body": "self"})  # still not self-notify for owner
    priv = Community.objects.create(institution=inst, name="Priv", description="d", visibility="private", created_by=owner)
    M.objects.create(community=priv, user=owner, role="owner")
    client.post(reverse("communities:join", args=[priv.pk]))
    assert Notification.objects.filter(user=owner, kind="community").count() == 1
    proj = Project.objects.create(institution=inst, creator=owner, title="Proj", description="d", team_size=3)
    PM.objects.create(project=proj, user=owner, role="lead")
    client.post(reverse("projects:apply", args=[proj.pk]), {"message": "me"})
    assert Notification.objects.filter(user=owner, kind="project").count() == 1
    circ = Circle.objects.create(institution=inst, name="Circ", purpose="p", created_by=owner, join_policy="approval")
    CM.objects.create(circle=circ, user=owner, role="owner")
    client.post(reverse("circles:join", args=[circ.pk]))
    assert Notification.objects.filter(user=owner, kind="circle").exists()
    # approval flows back to the requester
    login(client, owner)
    pm = CM.objects.get(circle=circ, user=other)
    client.post(reverse("circles:member_action", args=[circ.pk, pm.pk, "approve"]))
    assert Notification.objects.filter(user=other, kind="circle", title__contains="You're in").exists()


def test_no_self_notification_and_unsafe_urls_stripped(inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    assert notify(a, "reply", "x", actor=a) is None
    n = notify(b, "reply", "t", url="https://evil.example/phish", actor=a)
    m = notify(b, "reply", "t", url="//evil.example", actor=a)
    ok = notify(b, "reply", "t", url="/app/people/1/", actor=a)
    assert n.url == "" and m.url == "" and ok.url == "/app/people/1/"


def test_coalescing_by_ref(inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    notify(b, "message", "one", ref="k", actor=a); notify(b, "message", "two", ref="k", actor=a)
    assert Notification.objects.filter(user=b).count() == 1 and Notification.objects.get().title == "two"


def test_open_marks_read_redirects_and_is_private(client, inst):
    a, b, c = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb"), mk(inst, "c@x.edu", "Ccc")
    n = notify(b, "reply", "Hi", url="/app/events/", actor=a)
    login(client, c)
    assert client.get(reverse("notifications:open", args=[n.pk])).status_code == 404  # someone else's
    login(client, b)
    r = client.get(reverse("notifications:open", args=[n.pk]))
    n.refresh_from_db()
    assert r.status_code == 302 and r.url == "/app/events/" and n.is_read


def test_list_preview_count_and_mark_all(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    for i in range(3):
        notify(b, "reply", f"Item {i}", actor=a)
    login(client, b)
    assert client.get(reverse("notifications:count")).json() == {"unread": 3}
    assert b"Item 2" in client.get(reverse("notifications:preview")).content
    assert b"Item 1" in client.get(reverse("notifications:list")).content
    r = client.post(reverse("notifications:mark_all"), HTTP_X_REQUESTED_WITH="fetch")
    assert r.json() == {"unread": 0} and client.get(reverse("notifications:count")).json() == {"unread": 0}
    assert client.get(reverse("notifications:list"), {"tab": "unread"}).status_code == 200


def test_unread_badge_in_page_header(client, inst):
    a, b = mk(inst, "a@x.edu", "Aaa"), mk(inst, "b@x.edu", "Bbb")
    notify(b, "reply", "Ping", actor=a)
    login(client, b)
    html = client.get(reverse("dashboard:home")).content.decode()
    assert "data-notif-badge" in html and 'id="bell"' in html
    assert client.get(reverse("notifications:list")).status_code == 200


def test_all_phase5_pages_render_for_anonymous_redirect(client):
    for name in ("notifications:list", "messaging:inbox", "faculty:directory", "events:list"):
        assert client.get(reverse(name)).status_code == 302
