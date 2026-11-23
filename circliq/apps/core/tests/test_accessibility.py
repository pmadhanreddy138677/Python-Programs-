"""Automated accessibility regression checks (a subset of WCAG 2.1 AA that can be verified without a browser).

They do NOT replace manual testing with a screen reader and keyboard; see docs/SECURITY.md and docs/ARCHITECTURE.md.
"""
import io
import re
from collections import Counter
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management import call_command

from apps.accounts.models import User
from apps.ask.models import Question
from apps.circles.models import Circle
from apps.communities.models import Community
from apps.events.models import Event
from apps.messaging.models import Conversation
from apps.projects.models import Project

pytestmark = pytest.mark.django_db
ROOT = Path(settings.BASE_DIR)


def _name(el):
    if el.get("aria-label") or el.get("aria-labelledby") or el.get("title"):
        return True
    if el.get_text(strip=True):
        return True
    return any(i.get("alt") for i in el.find_all("img"))


def audit(html, url):
    soup, issues = BeautifulSoup(html, "html.parser"), []
    if not soup.html or not soup.html.get("lang"):
        issues.append("missing <html lang>")
    h1 = [h for h in soup.find_all("h1") if h.get_text(strip=True)]
    if len(h1) != 1:
        issues.append(f"{len(h1)} <h1> elements (need exactly 1)")
    if not soup.find("main", id="main"):
        issues.append("no <main id=main> landmark")
    if not soup.find("a", class_="skip-link"):
        issues.append("no skip link")
    for img in soup.find_all("img"):
        if img.get("alt") is None:
            issues.append(f"<img> without alt: {img.get('src')}")
    ids = Counter(e["id"] for e in soup.find_all(id=True))
    issues += [f"duplicate id '{i}' x{n}" for i, n in ids.items() if n > 1]
    labels_for = {l.get("for") for l in soup.find_all("label") if l.get("for")}
    for el in soup.find_all(["input", "select", "textarea"]):
        if el.get("type") in ("hidden", "submit", "button", "image"):
            continue
        ok = el.get("aria-label") or el.get("aria-labelledby") or (el.get("id") and el["id"] in labels_for) or el.find_parent("label")
        if not ok:
            issues.append(f"unlabelled <{el.name} name={el.get('name')}>")
    for el in soup.find_all(["button", "a"]):
        if el.name == "a" and not el.get("href"):
            continue
        if not _name(el):
            issues.append(f"{el.name} without an accessible name: {str(el)[:90]}")
    navs = soup.find_all("nav")
    if len(navs) > 1:
        issues += [f"<nav> without aria-label" for n in navs if not n.get("aria-label")]
    for h in soup.find_all(re.compile("^h[1-6]$")):
        if not h.get_text(strip=True):
            issues.append("empty heading")
    return [f"{url}: {i}" for i in issues]


@pytest.fixture
def pages(client):
    call_command("seed_demo", "--students=15", "--force", stdout=io.StringIO())
    me = User.objects.get(email="student1@demo.circliq.local")
    client.force_login(me)
    conv = Conversation.objects.filter(participants__user=me).first()
    comm, circ, proj = Community.objects.first(), Circle.objects.first(), Project.objects.first()
    urls = ["/app/", "/app/people/", f"/app/people/{me.pk}/", "/app/me/edit/", "/app/match/", "/app/match/?mode=study", "/app/communities/", f"/app/communities/{comm.pk}/",
            f"/app/communities/{comm.pk}/?tab=members", "/app/communities/new/", "/app/circles/", "/app/circles/new/", f"/app/circles/{circ.pk}/", f"/app/circles/{circ.pk}/?tab=tasks",
            f"/app/circles/{circ.pk}/?tab=sessions", f"/app/circles/{circ.pk}/?tab=resources", f"/app/circles/{circ.pk}/?tab=members", "/app/study/", "/app/study/new/",
            "/app/projects/", "/app/projects/new/", f"/app/projects/{proj.pk}/", f"/app/projects/{proj.pk}/?tab=tasks", "/app/events/", f"/app/events/{Event.objects.first().pk}/", "/app/events/new/",
            "/app/faculty/", f"/app/faculty/{User.objects.get(email='faculty1@demo.circliq.local').pk}/", "/app/faculty/announcements/", "/app/faculty/requests/",
            "/app/messages/", "/app/messages/new-group/", "/app/notifications/", "/app/ask/", "/app/ask/new/", f"/app/ask/{Question.objects.first().pk}/",
            "/app/connections/", "/app/saved/", "/app/search/?q=python", "/accounts/settings/", "/accounts/password-change/"]
    if conv:
        urls.append(f"/app/messages/{conv.pk}/")
    return client, urls


def test_logged_in_pages_pass_accessibility_checks(pages):
    client, urls = pages
    problems = []
    for url in urls:
        r = client.get(url)
        assert r.status_code == 200, (url, r.status_code)
        problems += audit(r.content.decode(), url)
    assert problems == [], "\n" + "\n".join(problems[:40])


def test_admin_and_public_pages_pass_accessibility_checks(client):
    call_command("seed_demo", "--students=5", "--force", stdout=io.StringIO())
    problems = []
    for url in ["/", "/accounts/login/", "/accounts/register/", "/accounts/password-reset/", "/accounts/reactivate/", "/accounts/verify/resend/"]:
        problems += audit(client.get(url).content.decode(), url)
    client.force_login(User.objects.get(email="admin@demo.circliq.local"))
    for url in ["/app/admin/", "/app/admin/users/", "/app/admin/communities/", "/app/admin/reports/", "/app/admin/audit/"]:
        problems += audit(client.get(url).content.decode(), url)
    assert problems == [], "\n" + "\n".join(problems[:40])


def test_current_page_is_exposed_to_assistive_tech(pages):
    client, _ = pages
    soup = BeautifulSoup(client.get("/app/communities/").content.decode(), "html.parser")
    current = [a.get_text(strip=True) for a in soup.select("[aria-current=page]")]
    assert any("Communities" in c for c in current), current


def test_error_pages_are_accessible(client):
    from django.test import RequestFactory
    from apps.accounts import views
    for fn in (views.error_403, views.error_404, views.error_500):
        html = fn(RequestFactory().get("/")).content.decode()
        # error pages are standalone (no app shell); they must still declare a language and have a single heading
        soup = BeautifulSoup(html, "html.parser")
        assert soup.html.get("lang") and len(soup.find_all("h1")) == 1


# ---------------- colour contrast (WCAG 2.1 AA) computed from the real CSS tokens ----------------
def _lum(h):
    h = h.lstrip("#"); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _tokens(block):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_design_tokens_meet_wcag_aa_contrast(theme):
    css = (ROOT / "static/css/app.css").read_text()
    base = _tokens(re.search(r":root\{(.*?)\}", css, re.S).group(1))
    t = {**base, **_tokens(re.search(r"html\.dark\{(.*?)\}", css, re.S).group(1))} if theme == "dark" else base
    text_pairs = [("text", "surface"), ("text", "bg"), ("muted", "surface"), ("muted", "bg"), ("muted", "surface-2"), ("primary", "surface"), ("primary", "surface-2"), ("primary", "bg"),
                  ("ok-text", "surface"), ("err-text", "surface"), ("warn-text", "surface"), ("cyan-text", "surface")]
    fails = [f"{a} on {b}: {_ratio(t[a], t[b]):.2f}" for a, b in text_pairs if _ratio(t[a], t[b]) < 4.5]
    fills = [("primary-strong", "#FFFFFF"), ("ok-strong", "#FFFFFF"), ("err-strong", "#FFFFFF"), ("violet", "#FFFFFF")]
    fails += [f"white on {a}: {_ratio(t[a], b):.2f}" for a, b in fills if _ratio(t[a], b) < 4.5]
    assert fails == [], f"{theme}: {fails}"
