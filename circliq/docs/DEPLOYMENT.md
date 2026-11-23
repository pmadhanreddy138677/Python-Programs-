# Deployment

Two routes: **A. Docker Compose** (recommended, one command) or **B. manual** on a Linux server. Both need a domain name pointing at the server.

> Status: the production settings, static-file pipeline and Daphne/PostgreSQL combination were exercised in development (see SECURITY.md). The **Docker image and Compose file were not built in the development environment** (Docker wasn't available), so expect to fix small things on your first build.

## Environment variables
| Variable | Required | Meaning |
|---|---|---|
| `SECRET_KEY` | yes | Long random string (production refuses to start without one) |
| `ALLOWED_HOSTS` | yes | Your domain(s), comma separated |
| `CSRF_TRUSTED_ORIGINS` | yes | `https://your.domain` |
| `DATABASE_URL` | yes | `postgres://user:password@host:5432/dbname` |
| `REDIS_URL` | recommended | `redis://host:6379/0`: shared channel layer, cache and rate limits |
| `ADMIN_URL` | recommended | Unguessable path for the Django admin, e.g. `manage-7f3k2/` |
| `TRUST_PROXY_HEADERS` | behind a proxy | `True` when Caddy/Nginx sets `X-Forwarded-*` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | yes | SMTP for verification and reset emails |
| `MEDIA_ROOT` | optional | Where uploads are stored (back this up) |
| `CSP_REPORT_ONLY` | optional | `True` to log CSP violations without blocking (useful while testing) |
| `SECURE_SSL_REDIRECT` | optional | `True` by default |

## A. Docker Compose
```bash
cp .env.production.example .env.production      # edit values
printf "POSTGRES_PASSWORD=choose-a-long-password\nDOMAIN=circliq.example.edu\n" > .env
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py make_admin you@example.edu
```
Caddy obtains HTTPS certificates automatically. The `web` container runs migrations on start and serves HTTP + WebSockets with Daphne.

## B. Manual (Ubuntu example)
1. Install Python 3.12, PostgreSQL, Redis, and a reverse proxy (Caddy or Nginx).
2. Create the database and user; set the environment variables (systemd `EnvironmentFile`).
3. `pip install -r requirements.txt`, then `python manage.py migrate` and `python manage.py collectstatic --noinput` with `DJANGO_SETTINGS_MODULE=config.settings.prod`.
4. Run `daphne -b 127.0.0.1 -p 8000 config.asgi:application` under systemd.
5. Proxy HTTPS to port 8000. **Forward WebSocket upgrades** (`Upgrade`/`Connection` headers) and set `client_max_body_size 8m` on Nginx.

## First-day setup
1. `make_admin` for the real administrator(s).
2. Admin site > **Institutions**: set **Allowed email domains**; review departments and programs.
3. Delete or edit the starter communities (they have no owner).
4. Never run `seed_demo` on the live database.

## Scheduled jobs
Event reminders: run `python manage.py send_event_reminders` **hourly** (cron, systemd timer, or Windows Task Scheduler). With Compose: `docker compose exec -T web python manage.py send_event_reminders`.

## Backups (do this before anyone relies on it)
- Database: nightly `pg_dump -Fc circliq > circliq-$(date +%F).dump`; copy off the server; **test a restore**.
- Uploads: back up the `media` volume / `MEDIA_ROOT`.
- Keep `.env.production` somewhere safe (it holds your secrets).

## Updating
`git pull` (or copy the new release), `docker compose up -d --build`. Migrations run automatically. Keep the previous database dump until you've checked the new version.

## Monitoring
- `GET /healthz/` returns `{"status": "ok"}` (200) or 503 if the database is unreachable. Point an uptime monitor at it.
- Logs go to stdout (`docker compose logs -f web`). Set `LOG_LEVEL=WARNING` to reduce noise.

## Scaling notes
Single server handles a campus-scale launch. If you need more: run several web containers (Redis is already shared), move uploads to object storage (e.g. `django-storages`), and put a CDN in front of `/static/`.

## Launch checklist
- [ ] Strong `SECRET_KEY`, real `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, custom `ADMIN_URL`
- [ ] Institution email domains set; first administrator created
- [ ] HTTPS working; `check --deploy` clean (HSTS preload warning is optional)
- [ ] SMTP tested (register a test account and receive the email)
- [ ] Backups running and a restore tested
- [ ] Reminder job scheduled
- [ ] Privacy notice, terms and a contact address agreed with the institution (the Privacy/Terms/Contact pages are placeholders)
- [ ] Tried on a phone and a laptop; keyboard and screen-reader pass
- [ ] Moderation plan: who reviews reports, and how quickly
