import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.circles.models import Circle, CircleMembership as M, CirclePost, CircleResource, CircleTask, StudySession
from apps.connections.models import Block, Connection
from apps.institutions.models import Institution
from apps.profiles.models import Skill
from apps.projects.models import Project, ProjectApplication, ProjectMembership as PM, ProjectTask
from apps.study.models import StudyRequest

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


def mkcircle(inst, owner, name="Circ", max_members=3, policy="open", **kw):
    c = Circle.objects.create(institution=inst, name=name, purpose="p", max_members=max_members, join_policy=policy, created_by=owner, **kw)
    M.objects.create(circle=c, user=owner, role="owner")
    return c


# ---------------- Circles ----------------
def test_create_circle_makes_owner(client, inst):
    u = mk(inst, "o@x.edu", "Owner"); login(client, u)
    r = client.post(reverse("circles:create"), {"name": "Py", "purpose": "learn", "category": "study", "max_members": 4, "join_policy": "open"})
    c = Circle.objects.filter(institution=inst).get()
    assert r.status_code == 302 and M.objects.get(circle=c, user=u).role == "owner"


def test_max_members_validation(client, inst):
    login(client, mk(inst, "o@x.edu", "Owner"))
    for bad in (1, 99):
        r = client.post(reverse("circles:create"), {"name": "X", "purpose": "p", "category": "general", "max_members": bad, "join_policy": "open"})
        assert r.status_code == 200
    assert not Circle.objects.filter(institution=inst).exists()


def test_capacity_enforced_open_join(client, inst):
    o, a, b = mk(inst, "o@x.edu", "O"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    c = mkcircle(inst, o, max_members=2)
    login(client, a); client.post(reverse("circles:join", args=[c.pk]))
    login(client, b); client.post(reverse("circles:join", args=[c.pk]))
    assert M.objects.filter(circle=c, status="active").count() == 2
    assert not M.objects.filter(circle=c, user=b).exists()


def test_approval_policy_and_capacity_on_approve(client, inst):
    o, a, b = mk(inst, "o@x.edu", "O"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    c = mkcircle(inst, o, max_members=2, policy="approval")
    login(client, a); client.post(reverse("circles:join", args=[c.pk]))
    login(client, b); client.post(reverse("circles:join", args=[c.pk]))
    ma, mb = M.objects.get(circle=c, user=a), M.objects.get(circle=c, user=b)
    assert ma.status == mb.status == "pending"
    assert client.post(reverse("circles:member_action", args=[c.pk, ma.pk, "approve"])).status_code == 404  # not owner
    login(client, o)
    client.post(reverse("circles:member_action", args=[c.pk, ma.pk, "approve"]))
    client.post(reverse("circles:member_action", args=[c.pk, mb.pk, "approve"]))  # circle now full
    ma.refresh_from_db(); mb.refresh_from_db()
    assert ma.status == "active" and mb.status == "pending"


def test_closed_circle_rejects_joins(client, inst):
    o, a = mk(inst, "o@x.edu", "O"), mk(inst, "a@x.edu", "A")
    c = mkcircle(inst, o, status="closed")
    login(client, a); client.post(reverse("circles:join", args=[c.pk]))
    assert not M.objects.filter(circle=c, user=a).exists()


def test_invite_only_connections_and_accept(client, inst):
    o, friend, stranger, blocked = (mk(inst, f"{n}@x.edu", n) for n in ("o", "friend", "stranger", "blocked"))
    Connection.objects.create(requester=o, receiver=friend, status="accepted")
    Connection.objects.create(requester=o, receiver=blocked, status="accepted")
    Block.objects.create(blocker=o, blocked=blocked)
    c = mkcircle(inst, o)
    login(client, o)
    assert client.post(reverse("circles:invite", args=[c.pk]), {"user": stranger.pk}).status_code == 404
    assert client.post(reverse("circles:invite", args=[c.pk]), {"user": blocked.pk}).status_code == 404
    client.post(reverse("circles:invite", args=[c.pk]), {"user": friend.pk})
    assert M.objects.get(circle=c, user=friend).status == "invited"
    login(client, friend)
    assert b"Accept invitation" in client.get(reverse("circles:detail", args=[c.pk])).content
    client.post(reverse("circles:respond_invite", args=[c.pk, "accept"]))
    assert M.objects.get(circle=c, user=friend).status == "active"


def test_workspace_hidden_from_non_members(client, inst):
    o, outsider = mk(inst, "o@x.edu", "O"), mk(inst, "x@x.edu", "Outsider")
    c = mkcircle(inst, o)
    CirclePost.objects.create(circle=c, author=o, body="SECRET-NOTE")
    s = StudySession.objects.create(circle=c, title="SECRET-SESSION", starts_at=timezone.now() + datetime.timedelta(days=1), created_by=o)
    CircleResource.objects.create(circle=c, added_by=o, title="SECRET-LINK", url="https://example.com")
    login(client, outsider)
    for tab in ("discussion", "tasks", "sessions", "resources", "members"):
        html = client.get(reverse("circles:detail", args=[c.pk]) + f"?tab={tab}").content.decode()
        assert "SECRET" not in html
    assert client.post(reverse("circles:post_new", args=[c.pk]), {"body": "hi"}).status_code == 404
    assert client.post(reverse("circles:session_delete", args=[s.pk])).status_code == 404
    assert client.post(reverse("circles:task_new", args=[c.pk]), {"title": "t"}).status_code == 404


def test_cross_institution_isolation(client, inst):
    other = Institution.objects.create(name="Other U", slug="other-u")
    ou = mk(other, "o@y.edu", "Outsider")
    c = mkcircle(inst, mk(inst, "o@x.edu", "O"))
    login(client, ou)
    assert client.get(reverse("circles:detail", args=[c.pk])).status_code == 404
    assert client.post(reverse("circles:join", args=[c.pk])).status_code == 404


def test_tasks_progress_and_move(client, inst):
    o, m2 = mk(inst, "o@x.edu", "O"), mk(inst, "m@x.edu", "M")
    c = mkcircle(inst, o); M.objects.create(circle=c, user=m2)
    login(client, o)
    client.post(reverse("circles:task_new", args=[c.pk]), {"title": "A", "assignee": m2.pk})
    client.post(reverse("circles:task_new", args=[c.pk]), {"title": "B"})
    a = CircleTask.objects.get(title="A")
    r = client.post(reverse("circles:task_move", args=[a.pk]), {"status": "done"}, HTTP_X_REQUESTED_WITH="fetch")
    assert r.json() == {"progress": 50}
    assert client.post(reverse("circles:task_move", args=[a.pk]), {"status": "bogus"}).status_code == 404
    login(client, m2)
    other_task = CircleTask.objects.get(title="B")
    assert client.post(reverse("circles:task_delete", args=[other_task.pk])).status_code == 404  # only creator/owner
    assert b"50%" in client.get(reverse("circles:detail", args=[c.pk])).content


def test_assignee_must_be_member(client, inst):
    o, outsider = mk(inst, "o@x.edu", "O"), mk(inst, "x@x.edu", "X")
    c = mkcircle(inst, o)
    login(client, o)
    client.post(reverse("circles:task_new", args=[c.pk]), {"title": "A", "assignee": outsider.pk})
    assert not CircleTask.objects.exists()


def test_sessions_must_be_future_and_resources_http_only(client, inst):
    o = mk(inst, "o@x.edu", "O"); c = mkcircle(inst, o); login(client, o)
    past = (timezone.localtime() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    soon = (timezone.localtime() + datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    base = {"title": "S", "duration_minutes": 60, "mode": "online", "location": "https://meet.example.com/x", "notes": ""}
    client.post(reverse("circles:session_new", args=[c.pk]), {**base, "starts_at": past})
    assert not StudySession.objects.exists()
    client.post(reverse("circles:session_new", args=[c.pk]), {**base, "starts_at": soon})
    assert StudySession.objects.count() == 1
    client.post(reverse("circles:resource_new", args=[c.pk]), {"title": "bad", "url": "javascript:alert(1)", "note": ""})
    client.post(reverse("circles:resource_new", args=[c.pk]), {"title": "ftp", "url": "ftp://x.com/f", "note": ""})
    assert not CircleResource.objects.exists()
    client.post(reverse("circles:resource_new", args=[c.pk]), {"title": "ok", "url": "https://example.com/doc", "note": "n"})
    assert CircleResource.objects.count() == 1
    assert b'rel="noopener noreferrer nofollow"' in client.get(reverse("circles:detail", args=[c.pk]) + "?tab=resources").content


def test_owner_cannot_leave_but_can_disband(client, inst):
    o = mk(inst, "o@x.edu", "O"); c = mkcircle(inst, o); login(client, o)
    client.post(reverse("circles:leave", args=[c.pk]))
    assert Circle.objects.filter(pk=c.pk).exists()
    client.post(reverse("circles:disband", args=[c.pk]))
    assert not Circle.objects.filter(pk=c.pk).exists()


def test_xss_escaped_in_circle_post(client, inst):
    o = mk(inst, "o@x.edu", "O"); c = mkcircle(inst, o); login(client, o)
    client.post(reverse("circles:post_new", args=[c.pk]), {"body": "<script>alert(1)</script>"})
    html = client.get(reverse("circles:detail", args=[c.pk])).content.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


# ---------------- Study Connect ----------------
def test_study_request_creates_linked_circle_and_join_fills_slots(client, inst):
    o, a, b = mk(inst, "o@x.edu", "Owner"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    login(client, o)
    r = client.post(reverse("study:create"), {"subject": "DBMS", "topic": "Joins", "goal": "Ace the exam", "description": "",
                                               "group_size": 2, "schedule": "Evenings", "mode": "online"})
    assert r.status_code == 302
    sr = StudyRequest.objects.get()
    c = sr.circle
    assert c.kind == "study" and c.max_members == 2 and M.objects.get(circle=c, user=o).role == "owner"
    login(client, a)
    assert b"DBMS" in client.get(reverse("study:list")).content
    client.post(reverse("circles:join", args=[c.pk]))
    login(client, b); client.post(reverse("circles:join", args=[c.pk]))  # full: owner + a
    assert M.objects.filter(circle=c, status="active").count() == 2 and not M.objects.filter(circle=c, user=b).exists()
    assert b"Full" in client.get(reverse("study:list")).content


def test_study_group_size_bounds(client, inst):
    login(client, mk(inst, "o@x.edu", "O"))
    r = client.post(reverse("study:create"), {"subject": "S", "topic": "T", "goal": "G", "group_size": 40, "schedule": "x", "mode": "either"})
    assert r.status_code == 200 and not StudyRequest.objects.exists()


# ---------------- Project Hub ----------------
def mkproject(inst, lead, size=3, **kw):
    p = Project.objects.create(institution=inst, creator=lead, title=kw.pop("title", "Proj"), description="d", team_size=size, **kw)
    PM.objects.create(project=p, user=lead, role="lead")
    return p


def test_create_project_lead_membership_and_skills(client, inst):
    u = mk(inst, "o@x.edu", "Lead"); login(client, u)
    py = Skill.objects.get(name="Python")
    r = client.post(reverse("projects:create"), {"title": "Chatbot", "description": "AI", "category": "ai_ml", "kind": "project",
                                                  "required_skills": [py.pk], "technologies": "Python", "team_size": 3, "goals": "ship"})
    p = Project.objects.get()
    assert r.status_code == 302 and PM.objects.get(project=p, user=u).role == "lead" and list(p.required_skills.all()) == [py]


def test_only_approved_faculty_can_post_mentorship(client, inst):
    stu, fac = mk(inst, "s@x.edu", "Stu"), mk(inst, "f@x.edu", "Prof", role="faculty")
    data = {"title": "Research", "description": "d", "category": "research", "kind": "research", "team_size": 3}
    login(client, stu)
    assert client.post(reverse("projects:create"), data).status_code == 200
    assert not Project.objects.exists()
    login(client, fac)  # faculty default is_approved=True from create_user
    client.post(reverse("projects:create"), data)
    assert Project.objects.get().kind == "research"
    fac.is_approved = False; fac.save()
    Project.objects.all().delete()
    login(client, fac)
    assert client.post(reverse("projects:create"), data).status_code == 302  # redirected: unapproved can't create
    assert not Project.objects.exists()


def test_apply_accept_flow_and_capacity(client, inst):
    lead, a, b = mk(inst, "l@x.edu", "Lead"), mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    p = mkproject(inst, lead, size=2)
    login(client, a); client.post(reverse("projects:apply", args=[p.pk]), {"message": "hi"})
    client.post(reverse("projects:apply", args=[p.pk]), {"message": "again"})  # duplicate
    login(client, b); client.post(reverse("projects:apply", args=[p.pk]), {"message": "me too"})
    assert ProjectApplication.objects.count() == 2
    aa, ab = ProjectApplication.objects.get(applicant=a), ProjectApplication.objects.get(applicant=b)
    assert client.post(reverse("projects:application", args=[aa.pk, "accept"])).status_code == 404  # applicant isn't lead
    login(client, lead)
    assert b"hi" in client.get(reverse("projects:detail", args=[p.pk]) + "?tab=applications").content
    client.post(reverse("projects:application", args=[aa.pk, "accept"]))
    client.post(reverse("projects:application", args=[ab.pk, "accept"]))  # team full
    ab.refresh_from_db()
    assert PM.objects.filter(project=p).count() == 2 and PM.objects.filter(project=p, user=a).exists() and ab.status == "pending"


def test_cannot_apply_when_closed_full_or_member(client, inst):
    lead, a = mk(inst, "l@x.edu", "Lead"), mk(inst, "a@x.edu", "A")
    closed, full = mkproject(inst, lead, title="Closed", status="closed"), mkproject(inst, lead, title="Full", size=2)
    PM.objects.create(project=full, user=mk(inst, "z@x.edu", "Z"))
    login(client, a)
    for p in (closed, full):
        client.post(reverse("projects:apply", args=[p.pk]))
    login(client, lead); client.post(reverse("projects:apply", args=[closed.pk]))
    assert not ProjectApplication.objects.exists()


def test_reject_withdraw_and_workspace_privacy(client, inst):
    lead, a, out = mk(inst, "l@x.edu", "Lead"), mk(inst, "a@x.edu", "A"), mk(inst, "o@x.edu", "Out")
    p = mkproject(inst, lead)
    ProjectTask.objects.create(project=p, title="SECRET-TASK", created_by=lead)
    login(client, out)
    html = client.get(reverse("projects:detail", args=[p.pk]) + "?tab=tasks").content.decode()
    assert "SECRET-TASK" not in html
    assert client.post(reverse("projects:task_new", args=[p.pk]), {"title": "x"}).status_code == 404
    assert client.post(reverse("projects:comment_new", args=[p.pk]), {"body": "x"}).status_code == 404
    assert client.get(reverse("projects:detail", args=[p.pk]) + "?tab=applications").status_code == 200  # falls back to overview
    login(client, a); client.post(reverse("projects:apply", args=[p.pk])); client.post(reverse("projects:withdraw", args=[p.pk]))
    assert not ProjectApplication.objects.exists()
    client.post(reverse("projects:apply", args=[p.pk]))
    app = ProjectApplication.objects.get()
    login(client, lead); client.post(reverse("projects:application", args=[app.pk, "reject"]))
    app.refresh_from_db()
    assert app.status == "rejected" and PM.objects.filter(project=p).count() == 1


def test_project_tasks_progress_status_and_member_management(client, inst):
    lead, m = mk(inst, "l@x.edu", "Lead"), mk(inst, "m@x.edu", "Mem")
    p = mkproject(inst, lead); mem = PM.objects.create(project=p, user=m)
    login(client, lead)
    client.post(reverse("projects:task_new", args=[p.pk]), {"title": "T1"})
    t = ProjectTask.objects.get()
    assert client.post(reverse("projects:task_move", args=[t.pk]), {"status": "done"}, HTTP_X_REQUESTED_WITH="fetch").json()["progress"] == 100
    client.post(reverse("projects:status", args=[p.pk]), {"status": "in_progress"})
    p.refresh_from_db(); assert p.status == "in_progress"
    login(client, m)
    assert client.post(reverse("projects:status", args=[p.pk]), {"status": "closed"}).status_code == 404
    assert client.post(reverse("projects:member_remove", args=[p.pk, mem.pk])).status_code == 404
    lm = PM.objects.get(project=p, user=lead)
    login(client, lead)
    assert client.post(reverse("projects:member_remove", args=[p.pk, lm.pk])).status_code == 404  # can't remove the lead
    client.post(reverse("projects:member_remove", args=[p.pk, mem.pk]))
    assert not PM.objects.filter(pk=mem.pk).exists()


def test_project_discussion_and_cross_institution(client, inst):
    lead = mk(inst, "l@x.edu", "Lead"); p = mkproject(inst, lead)
    login(client, lead)
    client.post(reverse("projects:comment_new", args=[p.pk]), {"body": "<b>kickoff</b>"})
    html = client.get(reverse("projects:detail", args=[p.pk]) + "?tab=discussion").content.decode()
    assert "&lt;b&gt;kickoff&lt;/b&gt;" in html
    other = Institution.objects.create(name="Other U", slug="other-u")
    login(client, mk(other, "o@y.edu", "Out"))
    assert client.get(reverse("projects:detail", args=[p.pk])).status_code == 404
    assert client.post(reverse("projects:apply", args=[p.pk])).status_code == 404


def test_skill_match_and_filters(client, inst):
    lead, me = mk(inst, "l@x.edu", "Lead"), mk(inst, "m@x.edu", "Me")
    py, js = Skill.objects.get(name="Python"), Skill.objects.get(name="JavaScript")
    p1 = mkproject(inst, lead, title="PyProj"); p1.required_skills.add(py)
    p2 = mkproject(inst, lead, title="JsProj", category="mobile"); p2.required_skills.add(js)
    me.profile.skills.add(py)
    login(client, me)
    html = client.get(reverse("projects:list")).content.decode()
    assert "PyProj" in html and "JsProj" in html and "You match 1 of 1 skills" in html
    html = client.get(reverse("projects:list"), {"skill": js.pk}).content.decode()
    assert "JsProj" in html and "PyProj" not in html
    assert "JsProj" not in client.get(reverse("projects:list"), {"category": "web"}).content.decode()
    assert "PyProj" in client.get(reverse("dashboard:home")).content.decode()  # recommended in the rail


def test_profile_shows_public_circles_only_to_visitors(client, inst):
    o, v = mk(inst, "o@x.edu", "Owner"), mk(inst, "v@x.edu", "Visitor")
    mkcircle(inst, o, name="Open-Circle-Name"); mkcircle(inst, o, name="Approval-Circle-Name", policy="approval")
    login(client, v)
    html = client.get(reverse("profiles:detail", args=[o.pk])).content.decode()
    assert "Open-Circle-Name" in html and "Approval-Circle-Name" not in html
    login(client, o)
    assert "Approval-Circle-Name" in client.get(reverse("profiles:detail", args=[o.pk])).content.decode()


def test_all_phase4_pages_render(client, inst):
    o = mk(inst, "o@x.edu", "Owner"); c = mkcircle(inst, o)
    CircleTask.objects.create(circle=c, title="t", created_by=o); CirclePost.objects.create(circle=c, author=o, body="b")
    CircleResource.objects.create(circle=c, added_by=o, title="r", url="https://example.com")
    StudySession.objects.create(circle=c, title="s", starts_at=timezone.now() + datetime.timedelta(days=1), created_by=o)
    p = mkproject(inst, o); ProjectTask.objects.create(project=p, title="pt", created_by=o)
    login(client, o)
    urls = [reverse("circles:list"), reverse("circles:list") + "?tab=mine", reverse("circles:list") + "?tab=invites", reverse("circles:create"), reverse("circles:edit", args=[c.pk]),
            *[reverse("circles:detail", args=[c.pk]) + f"?tab={t}" for t in ("discussion", "tasks", "sessions", "resources", "members")],
            reverse("study:list"), reverse("study:create"), reverse("projects:list"), reverse("projects:create"), reverse("projects:edit", args=[p.pk]),
            *[reverse("projects:detail", args=[p.pk]) + f"?tab={t}" for t in ("overview", "tasks", "discussion", "applications")],
            reverse("dashboard:home"), reverse("profiles:detail", args=[o.pk])]
    for url in urls:
        assert client.get(url).status_code == 200, url
