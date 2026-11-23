import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.ask.badges import badges_for, counts
from apps.ask.models import Answer, AnswerComment, AnswerVote, AskReport, Question, QuestionBookmark
from apps.communities.models import Community, CommunityMembership as M
from apps.connections.models import Block
from apps.discussions.models import Post
from apps.institutions.models import Institution
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMembership as PM

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


def mkq(inst, author, title="How do I normalise to 3NF?", **kw):
    return Question.objects.create(institution=inst, author=author, title=title, body=kw.pop("body", "details"), **kw)


def mka(q, author, body="Use this approach"):
    return Answer.objects.create(question=q, author=author, body=body)


def test_ask_question_validation_and_approval(client, inst):
    u = mk(inst, "u@x.edu", "User"); login(client, u)
    assert client.post(reverse("ask:new"), {"category": "academics", "title": "short", "body": "b"}).status_code == 200  # title too short
    r = client.post(reverse("ask:new"), {"category": "programming", "title": "How does Django ORM work?", "body": "explain"})
    q = Question.objects.get()
    assert r.status_code == 302 and q.author == u and q.institution == inst
    p = mk(inst, "p@x.edu", "Pending Prof", "faculty", approved=False); login(client, p)
    client.post(reverse("ask:new"), {"category": "career", "title": "A proper long title", "body": "b"})
    assert Question.objects.count() == 1


def test_answer_flow_notifications_and_one_per_user(client, inst):
    asker, helper = mk(inst, "a@x.edu", "Asker"), mk(inst, "h@x.edu", "Helper")
    q = mkq(inst, asker)
    login(client, helper)
    client.post(reverse("ask:answer", args=[q.pk]), {"body": "Here is a thorough answer"})
    client.post(reverse("ask:answer", args=[q.pk]), {"body": "Second try should not duplicate"})
    assert Answer.objects.count() == 1 and Notification.objects.filter(user=asker, title__contains="answered").count() == 1
    client.post(reverse("ask:answer", args=[q.pk]), {"body": "x"})  # too short is rejected before duplicate logic
    assert Answer.objects.count() == 1


def test_accept_only_by_asker_and_toggle(client, inst):
    asker, helper, other = mk(inst, "a@x.edu", "Asker"), mk(inst, "h@x.edu", "Helper"), mk(inst, "o@x.edu", "Other")
    q = mkq(inst, asker); a = mka(q, helper)
    login(client, other)
    assert client.post(reverse("ask:accept", args=[a.pk])).status_code == 404
    login(client, helper)
    assert client.post(reverse("ask:accept", args=[a.pk])).status_code == 404  # can't accept your own answer
    login(client, asker)
    client.post(reverse("ask:accept", args=[a.pk]))
    q.refresh_from_db()
    assert q.accepted_answer_id == a.pk and Notification.objects.filter(user=helper, title__contains="accepted").exists()
    detail = client.get(reverse("ask:detail", args=[q.pk])).content
    assert b"Solved" in detail and b"Unaccept" in detail
    client.post(reverse("ask:accept", args=[a.pk]))
    q.refresh_from_db()
    assert q.accepted_answer_id is None


def test_helpful_vote_toggle_no_self_vote(client, inst):
    asker, helper = mk(inst, "a@x.edu", "Asker"), mk(inst, "h@x.edu", "Helper")
    q = mkq(inst, asker); a = mka(q, helper)
    login(client, helper)
    assert client.post(reverse("ask:helpful", args=[a.pk])).status_code == 404
    login(client, asker)
    assert client.post(reverse("ask:helpful", args=[a.pk]), HTTP_X_REQUESTED_WITH="fetch").json() == {"active": True, "count": 1}
    assert client.post(reverse("ask:helpful", args=[a.pk]), HTTP_X_REQUESTED_WITH="fetch").json() == {"active": False, "count": 0}


def test_comments_bookmarks_and_permissions(client, inst):
    asker, helper, other = mk(inst, "a@x.edu", "Asker"), mk(inst, "h@x.edu", "Helper"), mk(inst, "o@x.edu", "Other")
    q = mkq(inst, asker); a = mka(q, helper)
    login(client, asker)
    client.post(reverse("ask:comment", args=[a.pk]), {"body": "Thanks, can you expand?"})
    c = AnswerComment.objects.get()
    assert Notification.objects.filter(user=helper, title__contains="commented").exists()
    login(client, other)
    assert client.post(reverse("ask:comment_delete", args=[c.pk])).status_code == 404
    client.post(reverse("ask:save", args=[q.pk]))
    assert QuestionBookmark.objects.filter(user=other).count() == 1
    assert "How do I normalise" in client.get(reverse("ask:list"), {"scope": "saved"}).content.decode()
    client.post(reverse("ask:save", args=[q.pk]))
    assert not QuestionBookmark.objects.exists()
    login(client, asker); client.post(reverse("ask:comment_delete", args=[c.pk]))
    assert not AnswerComment.objects.exists()


def test_list_filters_and_sorting(client, inst):
    u, v = mk(inst, "u@x.edu", "U"), mk(inst, "v@x.edu", "V")
    q1 = mkq(inst, u, "Alpha question about DBMS", category="academics")
    q2 = mkq(inst, u, "Beta question about Python", category="programming")
    q3 = mkq(inst, u, "Gamma solved question", category="programming")
    a3 = mka(q3, v); q3.accepted_answer = a3; q3.save()
    a2 = mka(q2, v)
    AnswerVote.objects.create(answer=a2, user=u)
    login(client, u)
    get = lambda **kw: client.get(reverse("ask:list"), kw).content.decode()
    assert "Alpha" in get(category="academics") and "Beta" not in get(category="academics")
    assert "Alpha" in get(status="unanswered") and "Beta" not in get(status="unanswered")
    h = get(status="solved"); assert "Gamma" in h and "Alpha" not in h
    assert "Beta" in get(status="open") and "Gamma" not in get(status="open")
    assert "Beta" in get(q="python")
    html = get(sort="helpful"); assert html.index("Beta") < html.index("Alpha")
    assert "Alpha" in get(scope="mine") and "Alpha" not in get(scope="answered")
    login(client, v); assert "Beta" in get(scope="answered")


def test_report_and_admin_moderation(client, inst):
    asker, helper, adm = mk(inst, "a@x.edu", "Asker"), mk(inst, "h@x.edu", "Helper"), mk(inst, "adm@x.edu", "Admin", "admin")
    q = mkq(inst, asker, "Spammy question here"); a = mka(q, helper, "Buy cheap stuff now")
    login(client, helper)
    client.post(reverse("ask:report_question", args=[q.pk]), {"reason": "spam"}); client.post(reverse("ask:report_question", args=[q.pk]), {"reason": "spam"})
    client.post(reverse("ask:report_answer", args=[a.pk]), {"reason": "spam"})  # own answer: rejected
    assert AskReport.objects.count() == 1
    assert client.get(reverse("ask:moderation")).status_code == 404
    login(client, adm)
    assert b"Spammy question" in client.get(reverse("ask:moderation")).content
    client.post(reverse("ask:resolve", args=[AskReport.objects.get().pk, "remove"]))
    q.refresh_from_db()
    assert q.is_removed and "Spammy question" not in client.get(reverse("ask:list")).content.decode()
    assert client.get(reverse("ask:detail", args=[q.pk])).status_code == 404


def test_isolation_blocking_and_escaping(client, inst):
    u, b = mk(inst, "u@x.edu", "U"), mk(inst, "b@x.edu", "Blocked")
    q = mkq(inst, b, "<script>alert(1)</script> title here", body="<img src=x onerror=1>")
    other = Institution.objects.create(name="Other U", slug="other-u")
    login(client, mk(other, "z@y.edu", "Zed"))
    assert client.get(reverse("ask:detail", args=[q.pk])).status_code == 404
    assert client.post(reverse("ask:answer", args=[q.pk]), {"body": "intruding answer"}).status_code == 404
    login(client, u)
    html = client.get(reverse("ask:list")).content.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    detail = client.get(reverse("ask:detail", args=[q.pk])).content.decode()
    assert "<img src=x" not in detail
    Block.objects.create(blocker=u, blocked=b)
    assert client.get(reverse("ask:detail", args=[q.pk])).status_code == 404
    assert "alert" not in client.get(reverse("ask:list")).content.decode()


def test_badge_rules(inst):
    me = mk(inst, "me@x.edu", "Me"); voters = [mk(inst, f"v{i}@x.edu", f"V{i}") for i in range(5)]
    asker = mk(inst, "a@x.edu", "Asker")
    answers = []
    for i in range(3):
        q = mkq(inst, asker, f"Question number {i} here"); a = mka(q, me); q.accepted_answer = a; q.save(); answers.append(a)
    for v in voters:
        AnswerVote.objects.create(answer=answers[0], user=v)
    AnswerVote.objects.create(answer=answers[1], user=me)  # self-vote must not count
    own_q = mkq(inst, me, "My own question here"); own_a = mka(own_q, me); own_q.accepted_answer = own_a; own_q.save()  # self-accepted must not count
    c = counts(me)
    assert c["helpful_peer"] == 5 and c["study_mentor"] == 3
    earned = {b["key"] for b in badges_for(me) if b["earned"]}
    assert {"helpful_peer", "study_mentor"} <= earned and "community_contributor" not in earned
    comm = Community.objects.create(institution=inst, name="C", description="d", created_by=me); M.objects.create(community=comm, user=me, role="owner")
    for i in range(6):
        Post.objects.create(community=comm, author=me, body=f"post {i}")
    assert counts(me)["community_contributor"] == 4 + 6 and "community_contributor" in {b["key"] for b in badges_for(me) if b["earned"]}
    for i in range(2):
        PM.objects.create(project=Project.objects.create(institution=inst, creator=asker, title=f"P{i}", description="d"), user=me)
    assert "project_collaborator" in {b["key"] for b in badges_for(me) if b["earned"]}


def test_ask_pages_render(client, inst):
    u, v = mk(inst, "u@x.edu", "U"), mk(inst, "v@x.edu", "V")
    q = mkq(inst, u); a = mka(q, v); AnswerComment.objects.create(answer=a, author=u, body="hi")
    login(client, u)
    for url in (reverse("ask:list"), reverse("ask:new"), reverse("ask:detail", args=[q.pk])):
        assert client.get(url).status_code == 200, url
    login(client, v)
    assert client.get(reverse("ask:detail", args=[q.pk])).status_code == 200
