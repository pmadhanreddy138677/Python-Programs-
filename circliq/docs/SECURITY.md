# Security

This document describes the controls in place, how they were checked in Phase 7, and what is **not** covered. Read the last section before launching with real students.

## Controls
| Area | Control | Where |
|---|---|---|
| Authentication | Email verification, Django password hashing (PBKDF2) and validators, login throttling per account+IP and per IP, reset/verification/registration/reactivation limits | `accounts/`, `core/ratelimit.py` |
| Roles | Public sign-up can only create students; faculty need admin approval; administrators are made only via `make_admin` or the Django admin | `accounts/forms.py`, `core/management/commands/make_admin.py` |
| Authorisation | Login required on every private route; objects fetched inside the viewer's institution; object-level checks (owner/moderator/author/receiver) return 404 | every `views.py` |
| Cross-campus isolation | Every query scoped by institution | all apps, covered by tests |
| CSRF | Django CSRF middleware; cookie is HttpOnly (JS reads a `<meta>` token) and SameSite=Lax | `settings/base.py` |
| XSS | Django auto-escaping; no `|safe`; chat text inserted with `textContent`; **strict CSP** with per-request nonce, no inline handlers | `core/security.py`, tests |
| Clickjacking / sniffing | `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff`, Referrer-Policy, Permissions-Policy, COOP | `core/security.py` |
| Transport | HTTPS redirect, HSTS, secure cookies, proxy header handling (production settings) | `settings/prod.py` |
| Uploads | Size/type limits, then **re-encoded with Pillow** (EXIF/GPS stripped, size bounded, decompression-bomb guard, random file names); media served only to signed-in users | `core/images.py`, `urls.py` |
| Rate limiting | Registration, login, password reset, posting, commenting, connection requests, creating things, search, and chat (HTTP and WebSocket) | `core/ratelimit.py` |
| WebSockets | Session authentication, participant check, origin validation, per-message limits, blocking enforced on every send | `messaging/consumers.py`, `config/asgi.py` |
| Privacy | Discoverability and Campus Match opt-out, blocking, deactivation, deletion (blocked if others depend on you), data export without other people's data | `accounts/`, `profiles/` |
| Admin | Dedicated Campus Admin area (403 for everyone else); append-only audit log; **private messages are never shown or registered in the Django admin**; admins cannot restrict other admins | `campusadmin/`, tests |
| Secrets & config | Everything from environment variables; production settings **refuse to start** with a weak/default `SECRET_KEY` or localhost-only `ALLOWED_HOSTS`; admin URL configurable | `settings/prod.py` |

## How it was reviewed (Phase 7)
- **Static analysis**: Bandit over `apps/` and `config/`: no medium or high findings; the two low findings (silent `except`) were replaced with logging. The final scan reports two low notes, both in `seed_demo` by design: a fixed password for *fictional demo accounts* and non-cryptographic `random` for fake data. The command refuses to run with `DEBUG` off.
- **Dependency audit**: `pip-audit` on `requirements.txt`: no known vulnerabilities at the time of the check. Re-run it regularly.
- **Django deployment check**: `check --deploy` with production settings: one intentional warning (HSTS preload is opt-in).
- **Access-control sweep**: an automated test walks all URL patterns (121+) and verifies anonymous GET/POST never reach private views.
- **Automated tests**: 181 tests, including CSRF enforcement, open-redirect refusal, CSP and header checks, escaped output, rate limits, upload sanitising, privacy flows, admin restrictions, and a check that no private message text reaches any admin page.
- **Real server run**: Daphne in production mode on PostgreSQL: security headers, hashed/compressed static files, cookie flags, hidden default admin URL, login-protected media, refused anonymous and wrong-origin WebSockets.
- **Database**: the whole suite passes on PostgreSQL 16 as well as SQLite.

## Known gaps and risks (be honest with yourself and your users)
1. **Email domain is not configured by default.** Until an administrator sets *Allowed email domains* on the institution, anyone can register. Set it before launch.
2. **Media authorisation is per-login, not per-object.** Uploaded images need a signed-in session and have unguessable names, but a signed-in user who learns an image URL could open it even if it belongs to a private community. For stricter isolation, serve media through an authorising proxy or signed URLs.
3. **Rate limits are per process** unless `REDIS_URL` is set (then they are shared).
4. **No two-factor authentication, CAPTCHA, malware scanning of non-image files (none accepted), or web application firewall.** Consider a CAPTCHA on registration if abuse appears.
5. **PBKDF2 hashing** (Django default). Argon2 (`argon2-cffi`) is stronger; switching needs only a settings change.
6. **Group chats** don't hide a blocked person's messages from the blocker (direct chats enforce blocking).
7. **No independent penetration test.** Automated tooling and tests are not a substitute. Do a review with your institution's security team before real use.
8. **Personal data law.** Students' data is personal data. Agree a privacy notice, retention policy and a contact for data requests with your institution; this project provides export/deletion tools, not legal compliance. (Not legal advice.)
9. **Accessibility** has automated checks only (labels, names, headings, landmarks, contrast). Test with a keyboard and a screen reader before launch.
10. **Browser rendering was not tested** in the development environment. Check the main pages on phone and desktop browsers.

## Reporting a problem
Treat any suspected vulnerability privately: tell the project owner directly rather than posting details publicly, and rotate `SECRET_KEY` if it may have leaked.
