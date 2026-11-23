# Circliq progress

## Phase 1 — Foundation (done, verified by running tests)
- [x] Project scaffold, split settings, .env config
- [x] Institutions (multi-institution ready), departments, programs, Marwadi starter data
- [x] Custom User (email login), roles, faculty approval flag
- [x] Register / email verification / login / logout / password reset / password change
- [x] Login throttling (5 failures -> 429 for 5 minutes), POST-only logout
- [x] Landing page, auth pages, dashboard shell, light/dark theme, 403/404/429/500 pages
- [x] 16 pytest tests passing; `check` and `makemigrations --check` clean

## Known limitations
- Tailwind via CDN (needs internet); standalone CLI build planned for Phase 7.
- Only Home works on the dashboard; other nav items are labelled with their phase.
- Email goes to the console in development; configure SMTP for production.
- Rate limiting uses local-memory cache (per process); use Redis/DB cache in production.
- Onboarding wizard, profile photo, interests: Phase 2.

## Phase 2 — Profiles and connections (done, 30 tests passing)
- [x] Profile model (auto-created), Interest/Skill seed data, avatar upload (2 MB, JPG/PNG/WebP)
- [x] 4-step onboarding wizard, progress saved to DB, skippable steps
- [x] Profile detail/edit, discoverability control
- [x] Discover: search, department/year/skill/interest filters, weighted explainable matching, pagination
- [x] Connections: request/accept/decline/cancel/remove, mutual-request auto-accept, blocking (both-way hiding)
- [x] Institution isolation and receiver-only authorization covered by tests
- [x] UI polish: shared app shell, icons, avatars, stats strip, completeness bar

## Phase 2 limitations
- Onboarding has 4 steps; the "first communities" step arrives with Phase 3 communities.
- Discovery ranks up to 500 candidates in Python (fine for one campus; move to SQL scoring at scale).
- Connection notifications arrive in Phase 5 (pending counts already shown).
- Uploaded images are validated but not re-encoded yet (Phase 7 hardening).

## Phase 3 — Communities and discussions (done, 52 tests passing)
- [x] Community, membership (owner / moderator / member; active / pending), public / private / official
- [x] Posts (discussion / question / project idea), comments with one reply level, reactions, bookmarks, accepted answers
- [x] Feed with For You / My Communities / Latest / Questions / Projects (deterministic ranking), pagination
- [x] Reports, moderation queue, direct removal, audit log (ModerationAction)
- [x] Private-community protection on every read and write path; cross-institution isolation; XSS escaping tested
- [x] Onboarding step "discover your first circle" with explainable recommendations
- [x] UI overhaul: new landing page, gradient mesh, icon tiles, scroll reveal, count-up stats, live reactions, community banners

## Phase 3 limitations
- Community tabs "Resources" and "Activities" are labelled as coming later (Phases 4–5).
- "Share within Circliq" is a copy-link button until messaging exists (Phase 5).
- Invitations to private communities arrive with Circles (Phase 4); for now people request to join.
- Posts are hard-deleted by their author; moderator removal is a soft delete (kept for audit).
- Notifications for replies/approvals arrive in Phase 5.

## Phase 4 — Circles, Study Connect, Project Hub (done, 77 tests passing)
- [x] Circles: capacity-enforced joining (row-locked on PostgreSQL), approval policy, invitations limited to connections, owner controls, disband
- [x] Circle workspace: discussion, task board with drag-and-drop and progress, sessions (future-only), resources (http/https only)
- [x] Study Connect: requests create linked study Circles; slot dots; join until full
- [x] Project Hub: skills, team size, deadline, applications, accept/reject with capacity check, tasks, discussion, status, faculty opportunities
- [x] Workspace privacy and cross-institution isolation covered by tests
- [x] Global input styling fix, new components (capacity ring, avatar stack, kanban, date tiles)

## Phase 4 limitations
- Circle discussion and resources are not covered by the report/moderation queue yet (owners can delete content).
- Sessions have no RSVP or reminders yet (reminders arrive with notifications, Phase 5).
- Project members have no separate "mentor" role; faculty opportunities use the same team model.
- Notifications for invites, applications and approvals arrive in Phase 5.

## Phase 5 — Messaging, Notifications, Faculty Connect, Events (done, 115 tests passing)
- [x] Django Channels + Daphne (ASGI); chat and notification consumers with session auth and origin validation
- [x] Conversations (direct + group), unread counts, history, typing, reconnect, HTTP fallback and polling fallback
- [x] Messaging rules: connections only (or faculty who allow DMs), blocking enforced on every send, participants-only access
- [x] Notification system with live push, coalescing, safe links; hooks in connections, communities, circles, projects, replies, messages, mentorship, announcements
- [x] Faculty directory/profile, mentorship requests, announcements with campus-wide notification
- [x] Events with capacity, save, register, official flag decided server-side, reminder command
- [x] Verified with real WebSocket tests and a live run against the Daphne server

## Phase 5 limitations
- "Load earlier messages" reloads the page with older history rather than prepending in place.
- Group chats don't hide a blocked person's messages from the blocker (direct chats enforce blocking fully).
- Event reminders need the scheduled command; they are not sent by a background worker.
- Faculty "question answering" and "resource sharing" are covered by communities and announcements; the dedicated Ask Circliq section is still unscheduled.
- No read receipts or online presence indicator yet.

## Phase 6 — Campus Match, recommendations, Ask Circliq (done, 140 tests passing)
- [x] Transparent weighted matching engine (friend / study / project) with reasons; opt-out; exclusions (blocked, hidden, other campus, unverified, faculty)
- [x] Voluntary match inputs on profiles (subjects, availability, collaboration style)
- [x] Dashboard "Picks for you" + profile nudges; global search with per-section privacy rules
- [x] Ask Circliq with answers, comments, helpful votes, accepted answers, bookmarks, reports, admin queue
- [x] Rule-based contribution badges with anti-gaming rules
- [x] Measured at 600 students: matching 60-100 ms / 8-9 queries; dashboard picks optimised 81 -> 36 ms (35 -> 19 queries)

## Phase 6 limitations
- Dashboard still runs ~49 queries and matching scans up to 500 candidates in Python per request. Fine for one campus; Phase 7 will batch and cache.
- Search is substring matching (no ranking or typo tolerance). PostgreSQL full-text search is planned for Phase 7.
- Ask Circliq: no editing of questions/answers yet; the flag buttons report as "inappropriate" (no reason picker yet); reports go to campus admins.
- Badges are computed live and not stored; there are no badge notifications yet.

## Phase 7 — Hardening, performance, accessibility, admin, docs, deployment (done, 181 tests passing)
- [x] Whole suite verified on PostgreSQL 16 as well as SQLite (it had only run on SQLite until now)
- [x] Security review: Bandit (no medium/high), pip-audit (clean), `check --deploy`, route-by-route access sweep, production-mode run
- [x] Strict CSP with nonces (no inline handlers), pre-compiled Tailwind (no CDN), security headers, hashed/compressed static files (WhiteNoise)
- [x] Rate limiting across sensitive endpoints; production settings refuse weak configuration; configurable admin URL; login-protected media
- [x] Upload re-encoding (EXIF/GPS stripped, bounded size, random names)
- [x] Privacy features: deactivation/reactivation, deletion with safeguards, data export
- [x] Campus Admin dashboard: analytics, users, faculty verification, restrictions, official communities, reports, append-only audit log
- [x] Performance: single-query unread count, N+1 fixes, prefetching (dashboard 61 -> 45 queries; picks 81 -> 36 ms)
- [x] Accessibility: automated audit found ~90 defects (unlabelled controls, nav labels, duplicate ids, contrast failures); all fixed; now a regression test
- [x] Deployment: Dockerfile, Compose (Postgres + Redis + Caddy), production env template, health check, scheduler guidance
- [x] `seed_demo` (fictional data) and `make_admin` commands; ARCHITECTURE, SECURITY, DEPLOYMENT, TESTING and USER_GUIDE docs

## Phase 7 limitations
See docs/SECURITY.md "Known gaps". Highlights: email domain must be configured before launch; media authorisation is per-login; no 2FA/CAPTCHA; no browser, screen-reader or load testing was possible here; the Docker image was not built here; search is substring-based (no ranking).

## Project status
All seven planned phases are complete. Remaining ideas: full-text search, 2FA, per-object media authorisation, editing in Ask Circliq, read receipts and presence, a mobile app or PWA, and an independent security review before a real launch.
