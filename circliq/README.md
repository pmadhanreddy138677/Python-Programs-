# circliq: Find Your Circle. Connect Beyond Classrooms.

A private, community-first campus platform where students meet people with shared interests, find study partners and project
teammates, join communities, talk to faculty, and discover events. Built with **Django, Channels (WebSockets), PostgreSQL and
Tailwind CSS** as a student project. *It is not affiliated with or endorsed by any university unless the institution says so.*

## What's inside

| Area | What it does |
|---|---|
| **Accounts & roles** | Email-verified registration, student / faculty / administrator roles, faculty approval, password reset, account deactivation, deletion and data export |
| **Profiles & Discover** | Onboarding wizard, interests, skills, goals, discoverability controls, search and filters |
| **Connections** | Requests, accept/decline, blocking (hidden both ways) |
| **Campus Match** | Friend, Study and Project matching with transparent, explainable scoring; opt-out |
| **Communities** | Public / private / official, membership approval, discussions, comments, reactions, bookmarks, reports, moderation queue |
| **Circles, Study Connect, Project Hub** | Small groups with tasks (drag-and-drop board), sessions, shared links; study requests; projects with applications and teams |
| **Messaging** | Real-time one-to-one and group chat, unread counts, typing, reconnect and HTTP fallback |
| **Notifications** | Live bell and toasts, notification page, event reminders |
| **Faculty Connect & Events** | Faculty directory, mentorship requests, announcements; events with registration and capacity |
| **Ask Circliq** | Campus Q&A with accepted answers, helpful votes, and rule-based contribution badges |
| **Campus Admin** | Analytics, user management, faculty verification, official communities, reports, audit log (never shows private messages) |

## Quick start on Windows (VS Code)

1. Install **Python 3.12 or 3.13** (tick *Add python.exe to PATH*), **VS Code** with the Python extension, and optionally Git.
2. In a VS Code terminal (PowerShell) inside the project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo           # optional: fictional people and activity so every screen has content
python manage.py runserver
```

Open http://127.0.0.1:8000. With `seed_demo`, log in as `student1@demo.circliq.local`, `faculty1@demo.circliq.local` or
`admin@demo.circliq.local` (password `Demo@12345!`). Verification emails print in the terminal.

**Your own admin account:** register normally (or `python manage.py createsuperuser`), then
`python manage.py make_admin you@example.com` and open **Campus admin** in the sidebar.

**Before real students sign up:** in the Django admin (`/admin/`) open *Institutions*, edit your institution, and set
**Allowed email domains**. Until you do, registration accepts any email address (fine for development, not for launch).
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the launch checklist.

### Python version note
`runserver` uses Daphne for WebSockets. On very new Python versions (3.14) Daphne's dependencies may not install yet. If
`pip install` fails on `daphne` or `channels-redis`, remove those two lines from `requirements.txt` and install the rest.
Everything still works; chat and notifications then update every few seconds instead of instantly.

### Tests
```powershell
python manage.py check
python -m pytest -q                              # SQLite (default)
$env:DATABASE_URL="postgres://user:pass@localhost:5432/circliq"; python -m pytest -q   # PostgreSQL
```
181 tests cover permissions, privacy, real-time messaging, security controls and accessibility. See [docs/TESTING.md](docs/TESTING.md).

### Styles
Tailwind is **pre-compiled** into `static/css/tailwind.css`, so no Node.js is needed. If you add new Tailwind classes to templates, rebuild
with the standalone CLI: `tailwindcss -c tailwind.config.js -i static/src/tailwind.input.css -o static/css/tailwind.css --minify`
([download](https://github.com/tailwindlabs/tailwindcss/releases/tag/v3.4.17)).

## Documentation
- [Architecture](docs/ARCHITECTURE.md): apps, data model, real-time design, key decisions
- [Security](docs/SECURITY.md): controls, review results, known gaps
- [Deployment](docs/DEPLOYMENT.md): Docker Compose or manual, environment variables, backups, launch checklist
- [Testing](docs/TESTING.md): what is tested and how
- [User guide](docs/USER_GUIDE.md): for students, faculty and administrators
- [Progress](docs/PROGRESS.md): phase-by-phase history and limitations

## Project layout
```
config/            settings (base/dev/prod), urls, asgi, routing
apps/              core, institutions, accounts, profiles, connections, dashboard, communities, discussions, moderation,
                   circles, study, projects, notifications, messaging, faculty, events, recommendations, ask, campusadmin
templates/  static/  deploy/  docs/  Dockerfile  docker-compose.yml
```
