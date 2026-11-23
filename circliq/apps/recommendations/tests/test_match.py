import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.communities.models import Community, CommunityMembership as M
from apps.connections.models import Block, Connection
from apps.discussions.models import Post
from apps.institutions.models import Institution
from apps.profiles.models import Interest, Skill
from apps.recommendations import engine
from apps.recommendations.services import nudges, picks_for, ranked_matches

PW = "Str0ng-Pass-9871"
db = pytest.mark.django_db


# ---------- pure engine tests (no database) ----------
def F(**kw):
    return engine.Features(**kw)


def test_friend_scoring_and_reasons():
    me = F(interests={"Anime", "Python", "Cricket"}, hobbies={"Anime", "Cricket"}, goals={"friends"}, availability={"wd_evening"}, year=2)
    o = F(interests={"Anime", "Cricket", "Music"}, hobbies={"Anime", "Cricket"}, goals={"friends"}, availability={"wd_evening", "we_morning"}, year=2)
    r = engine.friend(me, o)
    # 2 shared interests *3 + 2 hobby bonus + friends goal 4 + 1 slot + same year 1
    assert r.score == 6 + 2 + 4 + 1 + 1
    assert r.reasons[0] == "You both enjoy Anime and Cricket" and any("new friends" in x for x in r.reasons)


def test_friend_requires_some_overlap():
    assert engine.friend(F(interests={"A"}), F(interests={"B"})).score == 0
    assert engine.friend(F(year=2, availability={"wd_evening"}), F(year=2, availability={"wd_evening"})).score == 0


def test_study_scoring_subjects_are_case_insensitive():
    me = F(subjects={"dbms": "DBMS", "python": "Python"}, goals={"study"}, availability={"wd_evening"}, dept=1, year=2)
    o = F(subjects={"dbms": "dbms", "statistics": "Statistics"}, goals={"study"}, availability={"wd_evening"}, dept=1, year=2)
    r = engine.study(me, o)
    assert r.score == 6 + 4 + 2 + 1 + 1 and "You're both studying DBMS" in r.reasons[0]
    assert engine.study(F(subjects={"a": "A"}), F(subjects={"b": "B"})).score == 0


def test_project_scoring_complementary_skills():
    me = F(skills={"Python", "Django"}, goals={"projects"}, collab={"hackathons"}, tech={"Python"})
    o = F(skills={"Python", "UI/UX Design", "Figma"}, goals={"projects"}, collab={"hackathons"}, tech={"Python"})
    r = engine.project(me, o)
    assert r.score == (2 * 2) + 1 + 4 + 1 + 1
    assert "Brings Figma and UI/UX Design, which you don't list" == r.reasons[0]
    assert engine.project(F(skills={"A"}), F(skills={"A"})).score == 0  # only identical skills, no shared goal: not complementary


def test_strength_and_label_bounds():
    assert engine.strength("friend", 9) == 50 and engine.strength("friend", 500) == 100
    assert engine.label(80) == "Great match" and engine.label(50) == "Good match" and engine.label(10) == "Worth a look"


# ---------- database-backed ----------
@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email, name, role="student", interests=(), skills=(), subjects="", goals=(), discoverable=True, match=True, verified=True):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=verified, role=role)
    p = u.profile
    p.onboarding_complete, p.is_discoverable, p.match_enabled, p.study_subjects, p.goals = True, discoverable, match, subjects, list(goals)
    p.save()
    for n in interests:
        p.interests.add(Interest.objects.get(name=n))
    for n in skills:
        p.skills.add(Skill.objects.get(name=n))
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


@db
def test_ranked_matches_exclusions(inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python", "Anime"])
    good = mk(inst, "g@x.edu", "Good Match", interests=["Python", "Anime"])
    mk(inst, "h@x.edu", "Hidden", interests=["Python", "Anime"], discoverable=False)
    mk(inst, "o@x.edu", "OptedOut", interests=["Python", "Anime"], match=False)
    mk(inst, "f@x.edu", "Faculty", role="faculty", interests=["Python", "Anime"])
    mk(inst, "u@x.edu", "Unverified", interests=["Python", "Anime"], verified=False)
    blocked = mk(inst, "b@x.edu", "Blocked", interests=["Python", "Anime"])
    Block.objects.create(blocker=me, blocked=blocked)
    other = Institution.objects.create(name="Other U", slug="other-u")
    mk(other, "z@y.edu", "Foreign", interests=["Python", "Anime"])
    names = [r["user"].full_name for r in ranked_matches(me, "friend")]
    assert names == ["Good Match"]
    assert ranked_matches(me, "friend")[0]["reasons"][0] == "You both enjoy Anime and Python"


@db
def test_opted_out_user_gets_no_matches_and_ordering_is_deterministic(inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python", "Anime", "Music"], match=False)
    mk(inst, "a@x.edu", "Aaa", interests=["Python"]); mk(inst, "b@x.edu", "Bbb", interests=["Python"]); mk(inst, "c@x.edu", "Ccc", interests=["Python", "Anime"])
    assert ranked_matches(me, "friend") == []
    me.profile.match_enabled = True; me.profile.save()
    first = [r["user"].full_name for r in ranked_matches(me, "friend")]
    assert first == ["Ccc", "Aaa", "Bbb"] and first == [r["user"].full_name for r in ranked_matches(me, "friend")]
    assert ranked_matches(me, "bogus") == []


@db
def test_study_and_project_modes_in_db(inst):
    me = mk(inst, "me@x.edu", "Me", subjects="DBMS, Python", skills=["Python"], goals=["study", "projects"])
    mk(inst, "s@x.edu", "Study Buddy", subjects="dbms", goals=["study"])
    mk(inst, "p@x.edu", "Designer", skills=["UI/UX Design"], goals=["projects"])
    mk(inst, "n@x.edu", "Nobody")
    assert [r["user"].full_name for r in ranked_matches(me, "study")] == ["Study Buddy"]
    assert [r["user"].full_name for r in ranked_matches(me, "project")] == ["Designer"]


@db
def test_match_page_modes_toggle_and_privacy(client, inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python"], subjects="DBMS", skills=["Django"])
    mk(inst, "a@x.edu", "Alice Friend", interests=["Python"]); mk(inst, "s@x.edu", "Sam Study", subjects="DBMS")
    login(client, me)
    assert b"Alice Friend" in client.get(reverse("recommendations:match")).content
    assert b"Sam Study" in client.get(reverse("recommendations:match"), {"mode": "study"}).content
    assert client.get(reverse("recommendations:match"), {"mode": "nonsense"}).status_code == 200
    client.post(reverse("recommendations:match_toggle"))
    me.profile.refresh_from_db()
    assert me.profile.match_enabled is False
    html = client.get(reverse("recommendations:match")).content
    assert b"left Campus Match" in html and b"Alice Friend" not in html
    # while I'm opted out, nobody else is matched with me
    alice = User.objects.get(email="a@x.edu")
    assert "Me" not in [r["user"].full_name for r in ranked_matches(alice, "friend")]
    # opting back in makes me visible again; Alice opting out hides her in turn
    login(client, me); client.post(reverse("recommendations:match_toggle"))
    assert "Me" in [r["user"].full_name for r in ranked_matches(alice, "friend")]
    login(client, alice); client.post(reverse("recommendations:match_toggle"))
    me.refresh_from_db()
    assert "Alice Friend" not in [r["user"].full_name for r in ranked_matches(me, "friend")]


@db
def test_profile_edit_saves_match_inputs(client, inst):
    me = mk(inst, "me@x.edu", "Me")
    login(client, me)
    r = client.post(reverse("profiles:edit"), {"full_name": "Me", "bio": "", "study_subjects": "DBMS, OS", "availability": ["wd_evening", "we_morning"],
                                               "collab_preferences": ["online"], "is_discoverable": "on"})
    assert r.status_code == 302
    p = User.objects.get(pk=me.pk).profile
    assert p.subject_list() == ["DBMS", "OS"] and p.availability == ["wd_evening", "we_morning"] and p.collab_preferences == ["online"] and p.match_enabled is False


@db
def test_picks_and_nudges(client, inst):
    me = mk(inst, "me@x.edu", "Me", interests=["Python"], skills=["Python"])
    Community.objects.create(institution=inst, name="Python Hub", description="python stuff", category="technology")
    other = mk(inst, "o@x.edu", "Owner")
    from apps.projects.models import Project, ProjectMembership as PM
    p = Project.objects.create(institution=inst, creator=other, title="Py Project", description="d", team_size=3)
    p.required_skills.add(Skill.objects.get(name="Python")); PM.objects.create(project=p, user=other, role="lead")
    kinds = {x["kind"] for x in picks_for(me)}
    assert {"Community", "Project"} <= kinds
    assert all(x["url"].startswith("/app/") for x in picks_for(me))
    assert ("Add what you're studying", "Unlocks Study Match.", "/app/me/edit/") in nudges(me)
    login(client, me)
    html = client.get(reverse("dashboard:home")).content.decode()
    assert "Picks for you" in html and "Python Hub" in html and "Py Project" in html
    assert "studying" in html and "Unlocks Study Match" in html


@db
def test_search_scoping(client, inst):
    me, owner = mk(inst, "me@x.edu", "Me"), mk(inst, "o@x.edu", "Owner")
    mk(inst, "v@x.edu", "Zebra Visible"); mk(inst, "h@x.edu", "Zebra Hidden", discoverable=False)
    blocked = mk(inst, "b@x.edu", "Zebra Blocked"); Block.objects.create(blocker=me, blocked=blocked)
    other = Institution.objects.create(name="Other U", slug="other-u"); mk(other, "z@y.edu", "Zebra Foreign")
    pub = Community.objects.create(institution=inst, name="Open", description="d", created_by=owner)
    priv = Community.objects.create(institution=inst, name="Closed", description="d", visibility="private", created_by=owner)
    M.objects.create(community=pub, user=owner, role="owner"); M.objects.create(community=priv, user=owner, role="owner")
    Post.objects.create(community=pub, author=owner, body="zebra public post")
    Post.objects.create(community=priv, author=owner, body="zebra SECRET post")
    login(client, me)
    html = client.get(reverse("recommendations:search"), {"q": "zebra"}).content.decode()
    assert "Zebra Visible" in html and "zebra public post" in html
    for hidden in ("Zebra Hidden", "Zebra Blocked", "Zebra Foreign", "SECRET"):
        assert hidden not in html
    M.objects.create(community=priv, user=me)
    assert "SECRET" in client.get(reverse("recommendations:search"), {"q": "zebra"}).content.decode()


@db
def test_search_short_empty_and_escaped(client, inst):
    me = mk(inst, "me@x.edu", "Me"); login(client, me)
    assert b"at least two characters" in client.get(reverse("recommendations:search"), {"q": "a"}).content
    assert client.get(reverse("recommendations:search")).status_code == 200
    html = client.get(reverse("recommendations:search"), {"q": "<script>alert(1)</script>"}).content.decode()
    assert "<script>alert(1)</script>" not in html and "Nothing found" in html


@db
def test_profile_page_shows_badges_and_study_info(client, inst):
    me = mk(inst, "me@x.edu", "Me", subjects="DBMS"); me.profile.availability = ["wd_evening"]; me.profile.save()
    login(client, me)
    html = client.get(reverse("profiles:detail", args=[me.pk])).content.decode()
    assert "Helpful Peer" in html and "DBMS" in html and "Weekday evenings" in html and "not a university certificate" in html


@db
def test_best_per_mode_matches_full_ranking(inst):
    from apps.recommendations.services import best_per_mode
    me = mk(inst, "me@x.edu", "Me", interests=["Python", "Anime"], skills=["Python"], subjects="DBMS", goals=["study", "projects", "friends"])
    mk(inst, "a@x.edu", "Aaa", interests=["Python"], subjects="DBMS", skills=["Django"], goals=["study"])
    mk(inst, "b@x.edu", "Bbb", interests=["Python", "Anime"], skills=["UI/UX Design", "Git"], goals=["projects", "friends"])
    mk(inst, "c@x.edu", "Ccc", interests=["Anime"], subjects="DBMS", goals=["study", "friends"])
    best = best_per_mode(me)
    for mode in ("friend", "study", "project"):
        full = ranked_matches(me, mode)
        assert best[mode]["user"] == full[0]["user"] and best[mode]["reasons"] == full[0]["reasons"], mode
    me.profile.match_enabled = False; me.profile.save()
    assert best_per_mode(me) == {}
