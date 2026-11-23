# Testing

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q                      # 181 tests, SQLite
python -m pytest -q apps/core            # one area
$env:DATABASE_URL="postgres://user:pass@localhost:5432/circliq"; python -m pytest -q   # PostgreSQL
```
Last full run: **181 passed on SQLite and on PostgreSQL 16** (the PostgreSQL run was done just before the final test, `make_admin`, was added).

| Area | Tests | Highlights |
|---|---|---|
| core (security, a11y) | 26 | Route sweep (anonymous never reaches private views), CSRF, open redirects, CSP/headers, no inline handlers, no `|safe`, production settings refuse weak config, rate limits, upload sanitising (EXIF/GPS stripped), accessibility checks on ~40 pages, WCAG contrast of the design tokens, no wide fixed widths |
| circles (also study, projects) | 25 | Capacity under join/approve, invites limited to connections, workspace privacy, tasks, applications, faculty-only opportunities |
| accounts | 23 | Registration/verification/login rules, role escalation blocked, deactivate/reactivate, deletion rules, data export contents |
| communities (also discussions, moderation) | 22 | Private content protection, approvals, permissions, feed, reports and removal, XSS |
| recommendations | 15 | Scoring rules and reasons, exclusions, opt-out, search privacy, picks |
| messaging | 15 | Real WebSocket tests (send/receive, rejected users, blocking, typing, live notification), HTTP fallback, isolation |
| profiles (also connections) | 14 | Onboarding, discovery filters, connection and blocking rules |
| ask, notifications, events, campusadmin, faculty | 41 | Answers/votes/badge rules, notification hooks, event capacity and reminders, admin dashboard permissions and audit trail |

## What is *not* covered
- Real browsers: layout, animations, drag-and-drop and the chat UI were not exercised in a browser here. Check them by hand.
- Screen reader and keyboard-only use (only automated rules are tested).
- Load testing beyond a 600-student benchmark of matching and key pages.
- The Docker image build.

## Useful commands while testing
`python manage.py seed_demo` (fictional data) · `python manage.py send_event_reminders` · `python manage.py make_admin <email>`
