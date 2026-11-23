import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib import admin as django_admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import URLResolver, get_resolver, reverse
from PIL import Image

from apps.accounts.models import User
from apps.core.images import sanitize_image
from apps.core.ratelimit import hit
from apps.institutions.models import Institution

pytestmark = pytest.mark.django_db
PW = "Str0ng-Pass-9871"
ROOT = Path(settings.BASE_DIR)


@pytest.fixture
def inst():
    Institution.objects.update(is_active=False)
    return Institution.objects.create(name="Test U", slug="test-u")


def mk(inst, email="u@x.edu", name="U", role="student"):
    u = User.objects.create_user(email, PW, full_name=name, institution=inst, is_email_verified=True, role=role)
    u.profile.onboarding_complete = True
    u.profile.save()
    return u


def login(client, u):
    client.logout()
    assert client.login(username=u.email, password=PW)


# ---------------- access control ----------------
def _routes(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _routes(p.url_patterns, prefix + str(p.pattern))
        else:
            yield prefix + str(p.pattern)


def test_every_private_route_requires_login(client):
    """Sweeps ALL url patterns: anonymous users must be sent to login for GET and POST (nothing private is open)."""
    public = ("accounts/", "static/", "healthz/")
    admin_prefix = settings.ADMIN_URL
    checked, leaks = 0, []
    for route in _routes(get_resolver().url_patterns):
        if route == "" or route.startswith(public) or route.startswith(admin_prefix) or route.startswith("^media"):
            continue
        url = "/" + re.sub(r"<\w+:\w+>", lambda m: "1" if m.group(0).startswith("<int") else "x", route)
        checked += 1
        for method in ("get", "post"):
            r = getattr(client, method)(url)
            if r.status_code != 302 or "/accounts/login/" not in r.headers.get("Location", ""):
                leaks.append((method.upper(), url, r.status_code))
    assert checked > 100 and leaks == []


def test_media_requires_login(client, inst):
    assert client.get("/media/avatars/x.jpg").status_code == 302
    login(client, mk(inst))
    assert client.get("/media/avatars/x.jpg").status_code == 404  # signed in, but no such file


def test_csrf_is_enforced_on_state_changing_requests(inst):
    c = Client(enforce_csrf_checks=True)
    u = mk(inst)
    c.login(username=u.email, password=PW)
    assert c.post(reverse("accounts:logout")).status_code == 403
    assert c.post(reverse("discussions:create"), {"body": "x"}).status_code == 403


def test_open_redirects_are_refused(client, inst):
    a, b = mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    login(client, a)
    r = client.post(reverse("connections:send", args=[b.pk]), {"next": "https://evil.example/x"})
    assert r.status_code == 302 and "evil" not in r.headers["Location"]
    r = client.post(reverse("connections:send", args=[b.pk]), {"next": "//evil.example"})
    assert "evil" not in r.headers["Location"]
    client.logout()
    r = client.post(reverse("accounts:login"), {"username": a.email, "password": PW, "next": "https://evil.example/"})
    assert r.status_code == 302 and "evil" not in r.headers["Location"]


def test_message_bodies_are_not_exposed_in_django_admin():
    registered = {m.__name__ for m in django_admin.site._registry}
    assert "Message" not in registered
    from apps.campusadmin.admin import AuditLogAdmin
    assert AuditLogAdmin.has_add_permission(None, None) is False and AuditLogAdmin.has_change_permission(None, None) is False


# ---------------- headers & templates ----------------
def test_security_headers_and_csp_nonce(client, inst):
    r = client.get("/")
    csp = r.headers["Content-Security-Policy"]
    assert "script-src 'self' 'nonce-" in csp and "unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "object-src 'none'" in csp and "frame-ancestors 'none'" in csp and "base-uri 'self'" in csp
    assert r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "same-origin" and "camera=()" in r.headers["Permissions-Policy"]
    nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
    assert f'nonce="{nonce}"' in r.content.decode()  # the one inline script carries the matching nonce
    assert client.get("/").headers["Content-Security-Policy"] != csp  # fresh nonce on every response


def test_no_inline_handlers_or_unnonced_scripts_in_pages(client, inst):
    u = mk(inst); login(client, u)
    for url in ("/", "/app/", "/app/communities/", "/app/events/", "/app/messages/", "/app/people/", "/accounts/settings/"):
        html = client.get(url).content.decode()
        assert not re.search(r"\son(click|submit|change|input|load|error|focus)\s*=", html, re.I), url
        assert "javascript:" not in html.lower(), url
        for tag in re.findall(r"<script\b[^>]*>", html):
            assert "src=" in tag or "nonce=" in tag, (url, tag)


def test_templates_never_use_safe_or_autoescape_off():
    offenders = []
    for path in list((ROOT / "templates").rglob("*.html")):
        txt = path.read_text()
        if re.search(r"\|\s*safe\b|autoescape\s+off|mark_safe", txt):
            offenders.append(str(path.relative_to(ROOT)))
    for path in (ROOT / "apps").rglob("*.py"):
        if "tests" not in path.parts and "mark_safe" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], offenders


def test_cookie_and_csrf_settings():
    assert settings.SESSION_COOKIE_HTTPONLY and settings.CSRF_COOKIE_HTTPONLY
    assert settings.SESSION_COOKIE_SAMESITE == "Lax" and settings.X_FRAME_OPTIONS == "DENY"


def test_healthz(client):
    r = client.get("/healthz/")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def _run_prod(env):
    base = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL")}
    code = "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings.prod'; import config.settings.prod as s; print('LOADED', s.DEBUG, s.SESSION_COOKIE_SECURE, s.SECURE_SSL_REDIRECT)"
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**base, **env}, capture_output=True, text=True)


def test_production_settings_refuse_unsafe_configuration():
    assert "ImproperlyConfigured" in _run_prod({"ALLOWED_HOSTS": "circliq.example"}).stderr          # no SECRET_KEY
    assert "ImproperlyConfigured" in _run_prod({"SECRET_KEY": "short", "ALLOWED_HOSTS": "circliq.example"}).stderr
    assert "ImproperlyConfigured" in _run_prod({"SECRET_KEY": "k" * 60}).stderr                         # default localhost hosts
    ok = _run_prod({"SECRET_KEY": "k" * 60, "ALLOWED_HOSTS": "circliq.example"})
    assert "LOADED False True True" in ok.stdout, ok.stderr


# ---------------- rate limiting ----------------
def test_hit_counter_blocks_after_limit():
    assert [hit("k1", 3, 60) for _ in range(5)] == [True, True, True, False, False]


def test_registration_is_rate_limited_per_ip(client, inst):
    codes = [client.post(reverse("accounts:register"), {"email": "bad"}).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]


def test_posting_is_rate_limited(client, inst):
    from apps.communities.models import Community, CommunityMembership
    u = mk(inst)
    c = Community.objects.create(institution=inst, name="C", description="d", created_by=u)
    CommunityMembership.objects.create(community=c, user=u, role="owner")
    login(client, u)
    codes = [client.post(reverse("discussions:create"), {"community": c.pk, "kind": "discussion", "body": f"post {i}"}).status_code for i in range(32)]
    assert 429 not in codes[:30] and codes[30] == 429


def test_chat_flood_is_limited_for_all_transports(inst):
    from django.core.exceptions import ValidationError
    from apps.connections.models import Connection
    from apps.messaging import services as s
    a, b = mk(inst, "a@x.edu", "A"), mk(inst, "b@x.edu", "B")
    Connection.objects.create(requester=a, receiver=b, status="accepted")
    conv = s.get_or_create_direct(a, b)
    for i in range(60):
        s.post_message(conv, a, f"m{i}")
    with pytest.raises(ValidationError):
        s.post_message(conv, a, "one too many")


# ---------------- uploads ----------------
def _jpeg_with_exif_gps(size=(3000, 2000)):
    img = Image.new("RGB", size, (200, 40, 40))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"                 # Make
    exif[0x8825] = {1: "N", 2: (23.0, 1.0, 0.0), 3: "E", 4: (72.0, 5.0, 0.0)}   # GPS IFD
    buf = io.BytesIO(); img.save(buf, "JPEG", exif=exif)
    return SimpleUploadedFile("holiday.jpg", buf.getvalue(), "image/jpeg")


def test_sanitize_strips_metadata_resizes_and_renames():
    f = _jpeg_with_exif_gps()
    assert len(Image.open(io.BytesIO(f.read())).getexif()) > 0   # sanity: the input really has EXIF
    f.seek(0)
    out = sanitize_image(f)
    img = Image.open(io.BytesIO(out.read()))
    assert len(img.getexif()) == 0 and "exif" not in img.info                 # GPS/camera data gone
    assert max(img.size) <= 2000                                               # bounded
    assert re.fullmatch(r"[0-9a-f]{32}\.jpg", out.name) and out.content_type == "image/jpeg"   # unguessable name


def test_sanitize_rejects_non_images_and_wrong_formats():
    from django.core.exceptions import ValidationError
    for bad in (SimpleUploadedFile("a.jpg", b"<html>not an image</html>", "image/jpeg"), SimpleUploadedFile("a.jpg", b"GIF89a" + b"\x00" * 30, "image/jpeg")):
        with pytest.raises(ValidationError):
            sanitize_image(bad)
    buf = io.BytesIO(); Image.new("P", (10, 10)).save(buf, "GIF")
    with pytest.raises(ValidationError):
        sanitize_image(SimpleUploadedFile("a.gif", buf.getvalue(), "image/gif"))


def test_avatar_upload_is_sanitized_end_to_end(client, inst, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    u = mk(inst); login(client, u)
    r = client.post(reverse("profiles:edit"), {"full_name": "U", "bio": "", "avatar": _jpeg_with_exif_gps((800, 600)), "is_discoverable": "on", "match_enabled": "on"})
    assert r.status_code == 302
    u.profile.refresh_from_db()
    stored = Path(settings.MEDIA_ROOT) / u.profile.avatar.name
    assert "holiday" not in u.profile.avatar.name and stored.exists()
    assert len(Image.open(stored).getexif()) == 0
    bad = client.post(reverse("profiles:edit"), {"full_name": "U", "avatar": SimpleUploadedFile("x.jpg", b"not an image", "image/jpeg"), "is_discoverable": "on"})
    assert bad.status_code == 200


def test_no_oversized_fixed_widths_that_break_mobile():
    """Responsive guard: no hard-coded pixel width wider than a small phone (360px) in templates or CSS."""
    offenders = []
    for path in list((ROOT / "templates").rglob("*.html")) + [ROOT / "static/css/app.css"]:
        for m in re.finditer(r"(?<![-\w])(?:w|min-w)-\[(\d+)px\]|(?<![-\w])width:(\d+)px", path.read_text()):
            px = int(m.group(1) or m.group(2))
            if px > 360:
                offenders.append((str(path.relative_to(ROOT)), px))
    assert offenders == [], offenders


def test_make_admin_command(inst):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    su = User.objects.create_superuser("root@x.edu", PW, full_name="Root")
    assert su.institution_id is None
    call_command("make_admin", "root@x.edu", f"--institution={inst.slug}", stdout=io.StringIO())
    su.refresh_from_db()
    assert su.role == "admin" and su.institution == inst and su.is_approved
    with pytest.raises(CommandError):
        call_command("make_admin", "nobody@x.edu", stdout=io.StringIO())
