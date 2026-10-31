# Algoria — Django Edition

A personalized, gamified Python-learning platform. Students get an account,
an XP/level/streak system, a real coding playground, guided projects,
friend challenges and an AI-powered performance analysis. Teachers get a
dashboard to assign work and see where their class is struggling.

## Learning path

```
ALGORIA
  │
  ▼
👤 STUDENT PROFILE          (sign up, pick student or teacher)
  │
  ▼
🧠 PERSONAL ASSESSMENT       (short placement quiz)
  │
  ▼
🎯 PERSONALIZED PATH         (dashboard recommends a starting topic)
  │
  ┌──────────────┼──────────────┐
  ▼              ▼              ▼
📘 LEARN      🎮 PRACTICE     💻 CODE
(theory)     (topic quizzes)  (playground)
  └──────────────┼──────────────┘
                 ▼
          🏆 CHALLENGE          (daily challenge / friend challenge)
                 │
                 ▼
          🧪 PROJECT            (Build Something Real)
                 │
                 ▼
          📊 PERFORMANCE        (learning analytics)
                 │
                 ▼
          🤖 AI ANALYSIS        (Claude-powered read on your stats)
                 │
                 ▼
          🔄 NEXT RECOMMENDATION
```

## Topics covered

- **Module 1 · Python Fundamentals** — what a computer/program/algorithm is,
  the input → process → output model, Python syntax, variables, operators,
  data types, input/output
- **Module 2 · Control Flow & Functions** — conditions, loops, functions,
  modular program design
- **Module 3 · Data Structures** — lists, tuples, sets, dictionaries, strings
  & real-life data-handling examples
- **Module 4 · File Handling & Exception Handling** — reading/writing files
  with `open()`/`with`, `try`/`except`/`else`/`finally`, common built-in
  exceptions, raising your own errors

Every module has its own tab on the **Theory & Notes** page (with worked
examples), a matching set of **Practice** quiz topics, and — for Modules 1–4
overall — guided **Projects** (including two new ones: *Student Record
Logger* and *Safe Division Calculator* for file/exception handling).

## Features

0. **Aria, your guardian guide** — an original chibi guardian-spirit mascot
   (not based on any existing character) who pops up with a short tour the
   first time a new student or teacher reaches the dashboard, explaining
   what each part of the app does. Replayable anytime via the "✨ Ask Aria"
   button in the sidebar. Aria also appears in Animation Mode as the
   narrator for each step, and hovering any sidebar icon shows a short
   explanation from her of what that section does.
1. **Personalized dashboard** — level, XP progress bar, streak, current
   mission, badges, this week's activity, pending assignments/challenges.
2. **Real coding playground** — write and run actual Python in a
   locked-down sandbox (see "Sandbox safety" below).
3. **"Why did my code fail?"** — any error in the playground gets a plain-
   English explanation (what happened / why / how to fix it), not just a
   raw traceback.
4. **XP, levels, achievements** — a simple, transparent XP curve, 10 named
   levels (Beginner → Algoria Master), and 9 badges.
5. **Daily Learning Challenge** — one short 3-question round a day.
6. **Streak system with a streak freeze** — one missed day a week doesn't
   reset your streak; a friendly message replaces "you lost your streak."
7. **Build Something Real** — small guided projects (calculator, number
   guesser, grade calculator) with a checklist, starter code, and the same
   sandboxed runner as the playground.
8. **Teacher dashboard** — create assignments/challenges with a deadline,
   see every student's level/XP/streak/accuracy, and see which topics the
   whole class is weakest on.
9. **Learning analytics** — accuracy by topic, recent activity, and your
   overall stats.
10. **Friend challenges** — add a friend by username, challenge them to
    the same quiz, and compare scores head-to-head.
11. **Smart Revision Mode** — questions you get wrong come back for a
    quick recap a few days later, and drop out once you've got them twice
    in a row (light spaced repetition).
12. **Accessibility & customization** — light/dark mode, font size,
    comfortable/compact density, and a "reduce animations" toggle, all in
    Settings and in the 🎨 menu in the top bar. Preferences are saved to
    your account.

Plus a Theory & Practice notes mode, and the original 5-language 5-task
Game Mode "concept battle" — all still here, unauthenticated.

## Animation Mode: video library

Animation Mode is a grid of short animated lessons (thumbnail + play
button), one per topic — not literal video files, but the same lightweight
step-by-step scene player the app already used, now generalized to run
off simple data instead of one hardcoded sequence. Each lesson ends with
an "Open in Playground" button pre-loaded with example code, and a
"Practice this topic" link into the matching quiz.

- The original hand-built "Getting Started" lesson keeps its existing
  5-language translations and lives at `/animation/lesson/getting-started/`.
- The 14 topic lessons (`learning/animation_data.py`) are original written
  content, English-only for now.
- The step engine (`templates/animation_lesson.html`) supports five step
  kinds — `intro`, `code`, `diagram`, `list`, `try` — so adding a new
  lesson is just adding an entry to `LESSONS`, no new template needed.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000. The topic/question bank, badges and
project briefs are seeded automatically the first time a page that needs
them is visited — no separate import step.

Sign up as a **Student** to go through the learning path, or as a
**Teacher** to see the teacher dashboard instead (there's a role picker
on the sign-up page). A teacher account currently sees *all* students —
this is a single-classroom setup, not multi-class/multi-school.

## Setting up the Algoria tutor chat & AI Analysis

Both the chat bubble and the 🤖 AI Analysis page call the real Anthropic
API using **your own** API key — it's not bundled with the site.

1. Get an API key from [console.anthropic.com](https://console.anthropic.com).
2. Set it as an environment variable before starting the server:

   ```bash
   # macOS / Linux
   export ANTHROPIC_API_KEY="sk-ant-..."

   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY = "sk-ant-..."
   ```

3. Run the server as usual.

Without a key, the chat clearly explains what's missing instead of
failing, and AI Analysis falls back to a rule-based (non-AI) summary
built from the same stats — the recommendation is still real, just not
written by Claude.

Optional: set `ALGORIA_CHAT_MODEL` to override the default model
(`claude-sonnet-5`).

## Sandbox safety (Coding Playground & Projects)

Student code runs as a separate `python -I` (isolated mode) subprocess,
not inside the web server process, with:
- a CPU-time limit, memory limit, and a 5-second wall-clock timeout,
- network sockets, subprocess spawning, and filesystem-modifying calls
  blocked from inside the child process before the student's code runs,
- output capped in length.

This is **best-effort isolation suitable for a trusted classroom
setting**, not a hardened multi-tenant sandbox. If you deploy this
publicly on the open internet, put an additional container/VM boundary
around it (e.g. gVisor or a locked-down Docker container with no network
and a read-only filesystem) rather than relying on the subprocess
restrictions alone.

## Database

Student/teacher accounts and all gamification data (XP, levels, streaks,
badges, quiz attempts, questions, assignments, friend challenges,
projects) live in a local SQLite database (`db.sqlite3`), created by
`python manage.py migrate`. Sessions (used for guest-mode language/level/
purpose choices and in-progress quiz state) still live in a signed
cookie, not the database.

## Project layout

```
manage.py
algoria_project/         Django settings, root urls, wsgi/asgi
algoria_data.json        Translated UI strings + theory notes (Animation/Theory modes)
learning/
  models.py               Profile, Topic, Question, QuizAttempt, RevisionItem,
                           Badge, GameCompletion, Project, Assignment,
                           Friendship, FriendChallenge, DailyChallengeLog...
  gamification.py         XP curve, level titles, streak-freeze logic, badges
  quiz_engine.py          Shared quiz flow (practice/daily/assessment/revision/friend)
  sandbox.py              Locked-down code runner + "why did it fail" explanations
  ai_analysis.py          Claude-powered (with rule-based fallback) performance analysis
  seed.py                 ensure_seeded() — loads topics/questions/projects/badges
  chatbot.py               Algoria tutor: system prompt + Anthropic API call
  views.py, urls.py, context_processors.py, data.py (translations)
  templatetags/            {% t "key" %} translation tag, format_analysis filter
  static/learning/css/style.css   Full design system incl. light theme & a11y
templates/                 One template per page, extending base.html
```

## Before deploying anywhere public

- Change `SECRET_KEY` in `algoria_project/settings.py`.
- Set `DEBUG = False` and a real `ALLOWED_HOSTS` list.
- Put an extra sandboxing layer around the Coding Playground (see above).
- Run `python manage.py collectstatic` and serve `staticfiles/` via your
  web server (or a tool like WhiteNoise) instead of Django's dev server.
- Consider per-classroom scoping if you have more than one teacher — the
  teacher dashboard currently shows all students to all teachers.
