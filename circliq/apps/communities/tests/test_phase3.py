import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.communities.models import Community, CommunityMembership as M
from apps.discussions.models import Bookmark, Comment, Post, Reaction
from apps.institutions.models import Institution
from apps.moderation.models import ModerationAction, Report
from apps.profiles.models import Interest

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name, role="student", onboarded=True):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True, role=role)
    u.profile.onboarding_complete = onboarded
    u.profile.save()
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


def mkc(inst, owner, name="Py Club", visibility="public", **kw):
    c = Community.objects.create(institution=inst, name=name, description="d", visibility=visibility, created_by=owner, **kw)
    M.objects.create(community=c, user=owner, role="owner", status="active")
    return c


def mkpost(c, author, **kw):
    return Post.objects.create(community=c, author=author, body=kw.pop("body", "Hello world"), **kw)


def test_create_community_makes_owner(client, inst):
    u = mk(inst, "o@x.edu", "Owner")
    login(client, u)
    r = client.post(reverse("communities:create"), {"name": "Chess", "description": "Moves", "category": "general", "visibility": "public"})
    c = Community.objects.get(name="Chess")
    assert r.status_code == 302 and c.institution == inst and c.is_official is False
    assert M.objects.get(community=c, user=u).role == "owner"


def test_cannot_self_assign_official_or_duplicate_name(client, inst):
    u = mk(inst, "o@x.edu", "Owner")
    login(client, u)
    client.post(reverse("communities:create"), {"name": "Chess", "description": "x", "category": "general", "visibility": "public", "is_official": "on"})
    assert Community.objects.filter(institution=inst).get().is_official is False
    r = client.post(reverse("communities:create"), {"name": "chess", "description": "x", "category": "general", "visibility": "public"})
    assert r.status_code == 200 and Community.objects.filter(institution=inst).count() == 1


def test_unapproved_faculty_cannot_create(client, inst):
    f = mk(inst, "f@x.edu", "Prof", role="faculty")
    f.is_approved = False; f.save()
    login(client, f)
    client.post(reverse("communities:create"), {"name": "Lab", "description": "x", "category": "academics", "visibility": "public"})
    assert not Community.objects.filter(institution=inst).exists()


def test_public_join_instant_private_join_pending(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User")
    pub, priv = mkc(inst, o, "Pub"), mkc(inst, o, "Priv", "private")
    login(client, u)
    client.post(reverse("communities:join", args=[pub.pk]))
    client.post(reverse("communities:join", args=[priv.pk]))
    assert M.objects.get(community=pub, user=u).status == "active"
    assert M.objects.get(community=priv, user=u).status == "pending"


def test_private_content_hidden_from_non_members(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "Outsider")
    priv = mkc(inst, o, "Secret", "private")
    p = mkpost(priv, o, body="TOP-SECRET-BODY")
    login(client, u)
    body = client.get(reverse("communities:detail", args=[priv.pk])).content.decode()
    assert "TOP-SECRET-BODY" not in body and "private community" in body
    assert client.get(reverse("discussions:detail", args=[p.pk])).status_code == 404
    assert "TOP-SECRET-BODY" not in client.get(reverse("dashboard:home")).content.decode()
    assert client.post(reverse("discussions:react", args=[p.pk])).status_code == 404
    assert client.post(reverse("discussions:comment", args=[p.pk]), {"body": "hi"}).status_code == 404
    login(client, o)
    assert "TOP-SECRET-BODY" in client.get(reverse("dashboard:home")).content.decode()


def test_approval_flow_and_permissions(client, inst):
    o, u, other = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User"), mk(inst, "x@x.edu", "Other")
    priv = mkc(inst, o, "Priv", "private")
    m = M.objects.create(community=priv, user=u, status="pending")
    login(client, other)  # random member can't approve
    assert client.post(reverse("communities:member_action", args=[priv.pk, m.pk, "approve"])).status_code == 404
    login(client, o)
    assert client.post(reverse("communities:member_action", args=[priv.pk, m.pk, "approve"])).status_code == 302
    m.refresh_from_db()
    assert m.status == "active"
    assert ModerationAction.objects.filter(action="member_approve").exists()


def test_moderator_cannot_promote_or_remove_owner(client, inst):
    o, mod, mem = mk(inst, "o@x.edu", "Owner"), mk(inst, "m@x.edu", "Mod"), mk(inst, "u@x.edu", "Mem")
    c = mkc(inst, o)
    M.objects.create(community=c, user=mod, role="moderator")
    mm = M.objects.create(community=c, user=mem)
    om = M.objects.get(community=c, user=o)
    login(client, mod)
    assert client.post(reverse("communities:member_action", args=[c.pk, mm.pk, "promote"])).status_code == 404
    assert client.post(reverse("communities:member_action", args=[c.pk, om.pk, "remove"])).status_code == 404
    assert client.post(reverse("communities:member_action", args=[c.pk, mm.pk, "remove"])).status_code == 302
    assert not M.objects.filter(pk=mm.pk).exists()


def test_owner_cannot_leave_member_can(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User")
    c = mkc(inst, o)
    M.objects.create(community=c, user=u)
    login(client, o); client.post(reverse("communities:leave", args=[c.pk]))
    assert M.objects.filter(community=c, user=o).exists()
    login(client, u); client.post(reverse("communities:leave", args=[c.pk]))
    assert not M.objects.filter(community=c, user=u).exists()


def test_cross_institution_isolation(client, inst):
    other = Institution.objects.create(name="Other U", slug="other-u")
    ou = mk(other, "o@y.edu", "Outsider")
    c = mkc(inst, mk(inst, "o@x.edu", "Owner"))
    p = mkpost(c, c.created_by)
    login(client, ou)
    assert client.get(reverse("communities:detail", args=[c.pk])).status_code == 404
    assert client.post(reverse("communities:join", args=[c.pk])).status_code == 404
    assert client.get(reverse("discussions:detail", args=[p.pk])).status_code == 404
    assert "Py Club" not in client.get(reverse("communities:list")).content.decode()


def test_only_members_can_post_and_comment(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User")
    c = mkc(inst, o)
    p = mkpost(c, o)
    login(client, u)
    client.post(reverse("discussions:create"), {"community": c.pk, "kind": "discussion", "body": "sneaky"})
    assert Post.objects.count() == 1
    client.post(reverse("discussions:comment", args=[p.pk]), {"body": "nope"})
    assert Comment.objects.count() == 0
    client.post(reverse("communities:join", args=[c.pk]))
    client.post(reverse("discussions:create"), {"community": c.pk, "kind": "discussion", "body": "now ok"})
    client.post(reverse("discussions:comment", args=[p.pk]), {"body": "nice"})
    assert Post.objects.count() == 2 and Comment.objects.count() == 1


def test_question_needs_title_and_empty_body_rejected(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    c = mkc(inst, o)
    login(client, o)
    client.post(reverse("discussions:create"), {"community": c.pk, "kind": "question", "body": "why?"})
    client.post(reverse("discussions:create"), {"community": c.pk, "kind": "discussion", "body": "   "})
    assert not Post.objects.exists()


def test_edit_delete_only_by_author(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User")
    c = mkc(inst, o); M.objects.create(community=c, user=u)
    p = mkpost(c, o)
    login(client, u)
    assert client.post(reverse("discussions:edit", args=[p.pk]), {"title": "", "body": "hacked"}).status_code == 404
    assert client.post(reverse("discussions:delete", args=[p.pk])).status_code == 404
    login(client, o)
    client.post(reverse("discussions:edit", args=[p.pk]), {"title": "", "body": "edited"})
    p.refresh_from_db()
    assert p.body == "edited" and p.edited_at
    client.post(reverse("discussions:delete", args=[p.pk]))
    assert not Post.objects.exists()


def test_reaction_and_bookmark_toggle_json(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    p = mkpost(mkc(inst, o), o)
    login(client, o)
    r = client.post(reverse("discussions:react", args=[p.pk]), HTTP_X_REQUESTED_WITH="fetch")
    assert r.json() == {"active": True, "count": 1}
    assert client.post(reverse("discussions:react", args=[p.pk]), HTTP_X_REQUESTED_WITH="fetch").json() == {"active": False, "count": 0}
    client.post(reverse("discussions:save", args=[p.pk]))
    assert Bookmark.objects.count() == 1 and client.get(reverse("discussions:saved")).status_code == 200
    assert Reaction.objects.count() == 0


def test_reply_and_accepted_answer_rules(client, inst):
    o, u = mk(inst, "o@x.edu", "Asker"), mk(inst, "u@x.edu", "Helper")
    c = mkc(inst, o); M.objects.create(community=c, user=u)
    q = mkpost(c, o, kind="question", title="How?")
    login(client, u)
    client.post(reverse("discussions:comment", args=[q.pk]), {"body": "Like this"})
    top = Comment.objects.get()
    client.post(reverse("discussions:comment", args=[q.pk]), {"body": "reply", "parent": top.pk})
    assert Comment.objects.filter(parent=top).count() == 1
    assert client.post(reverse("discussions:accept", args=[q.pk, top.pk])).status_code == 404  # helper isn't the asker
    login(client, o)
    client.post(reverse("discussions:accept", args=[q.pk, top.pk]))
    q.refresh_from_db()
    assert q.accepted_comment_id == top.pk
    assert b"Accepted answer" in client.get(reverse("discussions:detail", args=[q.pk])).content


def test_xss_is_escaped(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    c = mkc(inst, o)
    mkpost(c, o, body="<script>alert(1)</script>", title="<b>x</b>")
    login(client, o)
    for url in (reverse("dashboard:home"), reverse("communities:detail", args=[c.pk])):
        html = client.get(url).content.decode()
        assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_feed_filters(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    c = mkc(inst, o)
    mkpost(c, o, body="plain-post"); mkpost(c, o, kind="question", title="Q-title", body="qq"); mkpost(c, o, kind="project", title="P-title", body="pp")
    login(client, o)
    q = client.get(reverse("dashboard:home"), {"feed": "questions"}).content.decode()
    assert "Q-title" in q and "P-title" not in q and "plain-post" not in q
    assert "P-title" in client.get(reverse("dashboard:home"), {"feed": "projects"}).content.decode()
    assert client.get(reverse("dashboard:home"), {"feed": "bogus"}).status_code == 200


def test_report_and_moderation_removal(client, inst):
    o, u, bad = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "Reporter"), mk(inst, "b@x.edu", "Poster")
    c = mkc(inst, o); M.objects.create(community=c, user=u); M.objects.create(community=c, user=bad)
    p = mkpost(c, bad, body="spammy")
    login(client, u)
    client.post(reverse("moderation:report_post", args=[p.pk]), {"reason": "spam", "details": ""})
    client.post(reverse("moderation:report_post", args=[p.pk]), {"reason": "spam", "details": ""})  # duplicate ignored
    r = Report.objects.get()
    assert client.get(reverse("moderation:queue", args=[c.pk])).status_code == 404  # reporter isn't a moderator
    assert client.post(reverse("moderation:resolve", args=[r.pk, "remove"])).status_code == 404
    login(client, o)
    assert b"spammy" in client.get(reverse("moderation:queue", args=[c.pk])).content
    client.post(reverse("moderation:resolve", args=[r.pk, "remove"]))
    p.refresh_from_db(); r.refresh_from_db()
    assert p.is_removed and r.status == "resolved"
    assert ModerationAction.objects.filter(action="remove_post").exists()
    assert "spammy" not in client.get(reverse("dashboard:home")).content.decode()
    assert client.get(reverse("discussions:detail", args=[p.pk])).status_code == 404


def test_cannot_report_own_post_and_direct_remove_needs_manager(client, inst):
    o, u = mk(inst, "o@x.edu", "Owner"), mk(inst, "u@x.edu", "User")
    c = mkc(inst, o); M.objects.create(community=c, user=u)
    p = mkpost(c, u)
    login(client, u)
    client.post(reverse("moderation:report_post", args=[p.pk]), {"reason": "spam"})
    assert not Report.objects.exists()
    assert client.post(reverse("moderation:remove_post", args=[p.pk])).status_code == 404
    login(client, o)
    client.post(reverse("moderation:remove_post", args=[p.pk]))
    p.refresh_from_db()
    assert p.is_removed


def test_official_only_by_admin(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    admin = User.objects.create_user("a@x.edu", PW, full_name="Admin", institution=inst, is_email_verified=True, role="admin")
    c = mkc(inst, o)
    login(client, o)
    assert client.post(reverse("communities:official", args=[c.pk])).status_code == 404
    login(client, admin)
    client.post(reverse("communities:official", args=[c.pk]))
    c.refresh_from_db()
    assert c.is_official
    assert client.get(reverse("communities:detail", args=[c.pk])).status_code == 200  # admins can manage without membership


def test_recommendations_and_onboarding_join(client, inst):
    u = mk(inst, "u@x.edu", "Newbie", onboarded=False)
    u.profile.interests.add(Interest.objects.get(name="Python"))
    Community.objects.create(institution=inst, name="Python Fans", description="All about python", category="technology")
    Community.objects.create(institution=inst, name="Cricket", description="bat", category="sports")
    u.profile.onboarding_step = 4; u.profile.save()
    login(client, u)
    body = client.get(reverse("profiles:onboarding", args=[4])).content.decode()
    assert "Python Fans" in body and "Cricket" not in body
    c = Community.objects.get(name="Python Fans")
    client.post(reverse("profiles:onboarding", args=[4]), {"join": c.pk})
    assert M.objects.filter(community=c, user=u, status="active").exists()


def test_seeded_communities_exist_for_marwadi():
    assert Community.objects.filter(institution__slug="marwadi-university", name="Python Learners").exists()


def test_all_phase3_pages_render(client, inst):
    o = mk(inst, "o@x.edu", "Owner")
    c = mkc(inst, o, "Pages")
    p = mkpost(c, o)
    Comment.objects.create(post=p, author=o, body="c")
    login(client, o)
    urls = [reverse("communities:list"), reverse("communities:create"), reverse("communities:edit", args=[c.pk]),
            *[reverse("communities:detail", args=[c.pk]) + f"?tab={t}" for t in ("discussions", "questions", "members", "about")],
            reverse("discussions:detail", args=[p.pk]), reverse("discussions:edit", args=[p.pk]), reverse("discussions:saved"),
            reverse("moderation:queue", args=[c.pk]), reverse("dashboard:home"), reverse("landing")]
    for url in urls:
        assert client.get(url).status_code == 200, url
