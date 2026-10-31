# 🎓 Algoria — Learn • Play • Master Python

**Algoria** is a gamified, personalized Python-learning platform built with **Django**. Students follow a structured learning path with quizzes, animated lessons, a sandboxed coding playground, guided projects, XP, levels, streaks and badges, while teachers get a dashboard to assign work and see where the class is struggling.

> Built as a college project.

---

## ✨ Features

### For students
- **Personalized dashboard** — level, XP progress bar, streak, badges, weekly activity and pending assignments
- **Placement assessment** — a short quiz that recommends where to start
- **Topic practice** — 5-question quizzes with hints and a short explanation for every answer
- **Daily challenge** — one quick challenge a day to keep your streak going
- **Streaks with a Streak Freeze** — one free missed day per week, with friendly messaging instead of guilt
- **XP, levels and achievements** — 10 named levels (Beginner → Algoria Master) and unlockable badges
- **Real coding playground** — write and run actual Python in the browser inside an isolated subprocess
- **"Why did my code fail?"** — errors are turned into a plain-English *what happened / why / how to fix it* card
- **Build Something Real** — guided mini-projects (calculator, number guesser, grade calculator, safe file logger)
- **Smart Revision Mode** — questions you got wrong come back later until you master them (lightweight spaced repetition)
- **Friend challenges** — add a friend and compare scores on the same quiz
- **Learning analytics** — accuracy by topic, recent activity, strongest and weakest areas
- **AI Analysis** — a personalized written summary of your progress and a next-topic recommendation
- **Animation Mode** — a video-library style grid of short animated lessons, one per topic
- **Aria, the guardian mascot** — an original chibi character who gives an onboarding tour, explains each sidebar section on hover, and narrates the animated lessons
- **Accessibility and customization** — dark/light theme, font size, compact/comfortable density, reduced animations
- **Tutor chatbot** — a floating chat assistant for Python questions

### For teachers
- Class overview of every student's level, XP, streak and accuracy
- Weak-topic chart across the whole class
- Create assignments and challenges with an optional topic and deadline

---

## 📚 Curriculum

| Module | Topics |
|---|---|
| **1 — Python Fundamentals** | Python Syntax, Variables, Operators, Data Types, Input & Output |
| **2 — Control Flow and Functions** | Conditions, Loops, Functions, Modular Program Design |
| **3 — Data Structures** | Lists, Tuples, Sets, Dictionaries, Strings & Data Handling |
| **4 — File Handling and Exception Handling** | File Handling, Exception Handling |

Each topic has an animated lesson, quiz questions with explanations, and a "try it" step that opens the Playground with example code preloaded.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Django |
| Database | SQLite (via Django ORM and migrations) |
| Frontend | Django templates, vanilla HTML/CSS/JavaScript (no framework, no build step) |
| Mascot and graphics | Inline SVG animated with CSS |
| AI features (optional) | Anthropic API (`anthropic` Python package) |
| Fonts | Google Fonts (Space Grotesk, Inter, JetBrains Mono) |

### Why a web app (Django) and not a desktop app (CustomTkinter)?
Algoria needs **multiple user accounts, a shared teacher dashboard, friend challenges and a central question bank**. That requires one shared backend many users connect to, which Django provides out of the box. A web app also needs no installation for students, supports much richer UI through CSS, and lets the code playground run server-side behind a controlled security boundary.

---

## 🏗️ Architecture

```
Browser → Django URL router → View → ORM (models) / business logic → Template → HTML response
```

```
algoria_project/        Django settings and root URLs
learning/
  models.py             16 database models
  views.py              page and action handlers
  urls.py               URL routing
  seed.py               topics, questions and projects (auto-seeded, idempotent)
  animation_data.py     content for the Animation Mode lessons
  gamification.py       XP curve, levels, streaks, badges
  quiz_engine.py        shared engine for practice/daily/assessment/revision/friend quizzes
  sandbox.py            isolated code runner and error explainer
  ai_analysis.py        AI-written (or rule-based fallback) performance summary
  chatbot.py            tutor chatbot
templates/              one HTML template per page
learning/static/        stylesheet
```

---

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. (Recommended) create a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the database
python manage.py migrate

# 5. Run the server
python manage.py runserver
```

Open **http://127.0.0.1:8000**, sign up as a **Student** or a **Teacher**, and you're in. Topics, questions and projects load automatically the first time they're needed.

### Optional: enable the AI features
The tutor chatbot and AI Analysis page use your own Anthropic API key. Without a key, both still work in a basic mode and tell you what's missing.

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="your-key-here"

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "your-key-here"
```

Never commit your API key to the repository.

---

## 🔒 Security Notes

- Uses Django's built-in CSRF protection, password hashing and session handling.
- The Coding Playground runs student code in an isolated subprocess with time and memory limits and blocked risky operations. This is **suitable for a trusted classroom**, not a hardened public sandbox. For public deployment, add a container or VM boundary (for example Docker with no network and a read-only filesystem).
- Before deploying publicly: change `SECRET_KEY`, set `DEBUG = False`, configure `ALLOWED_HOSTS`, and serve static files through a production web server.

---

## ⚠️ Known Limitations

- The teacher dashboard is single-classroom: every teacher sees every student.
- Per-topic Animation lessons are English-only; only the original "Getting Started" lesson and the legacy theory notes are available in five languages.
- The playground sandbox is not hardened for untrusted public use (see above).

---

## 🗺️ Roadmap

- Translate all animated lessons into Hindi, Telugu, Gujarati and Marathi
- Per-class scoping for teachers
- Container-based sandbox for the Playground
- Dedicated written notes page per topic

---

## 📸 Screenshots

_Add screenshots here: dashboard, practice quiz, playground, animation library, teacher dashboard._

---

## 📄 License

_Add a license of your choice (for example MIT)._
