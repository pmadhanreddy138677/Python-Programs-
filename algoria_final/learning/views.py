import json
import random
from datetime import timedelta

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import ai_analysis, chatbot, data, gamification, quiz_engine, sandbox
from .models import (
    Assignment, AssignmentCompletion, DailyChallengeLog, FriendChallenge, Friendship,
    GameCompletion, Profile, Project, ProjectSubmission, Question, QuestionAttempt,
    QuizAttempt, RevisionItem, Topic, UserBadge,
)
from .seed import ensure_seeded


def _t(request, key, **kwargs):
    lang = request.session.get("lang", "en")
    return data.t(lang, key, **kwargs)


# ---------------------------------------------------------------- landing --
def landing(request):
    return render(request, "landing.html")


# ------------------------------------------------------------- accounts --
def signup_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        display_name = (request.POST.get("display_name") or "").strip()
        password = request.POST.get("password") or ""
        password2 = request.POST.get("password2") or ""
        role = request.POST.get("role") if request.POST.get("role") in ("student", "teacher") \
            else "student"

        if not username or not password:
            error = "Please enter a username and password."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != password2:
            error = "Passwords don't match."
        elif User.objects.filter(username__iexact=username).exists():
            error = "That username is already taken."
        else:
            try:
                user = User.objects.create_user(username=username, password=password)
            except IntegrityError:
                error = "That username is already taken."
            else:
                Profile.objects.create(user=user, display_name=display_name, role=role)
                auth_login(request, user)
                return redirect("dashboard")

    return render(request, "signup.html", {"error": error})


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect("dashboard")
        error = "Incorrect username or password."

    return render(request, "login.html", {"error": error})


def logout_view(request):
    auth_logout(request)
    return redirect("landing")


@login_required(login_url="login_page")
def dashboard_page(request):
    ensure_seeded()
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.is_teacher:
        return redirect("teacher_dashboard")

    level, xp_into_level, xp_needed = gamification.level_progress(profile.xp)
    if profile.level != level:
        profile.level = level
        profile.save(update_fields=["level"])

    gamification.sync_badge_definitions()
    earned_slugs = set(
        UserBadge.objects.filter(user=request.user).values_list("badge__slug", flat=True)
    )
    all_badges = list(gamification.Badge.objects.all())
    badges = [{"badge": b, "earned": b.slug in earned_slugs} for b in all_badges]

    game_completions = GameCompletion.objects.filter(user=request.user)
    quiz_attempts = QuizAttempt.objects.filter(user=request.user)
    completed_count = game_completions.count() + quiz_attempts.count()

    correct_answers = sum(c.score // 10 for c in game_completions) + \
        sum(a.score for a in quiz_attempts)
    total_answers = sum(c.max_score // 10 for c in game_completions) + \
        sum(a.total for a in quiz_attempts)
    accuracy = round(100 * correct_answers / total_answers) if total_answers else None

    xp_pct = int(100 * xp_into_level / xp_needed) if xp_needed else 0

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    active_dates = set(quiz_attempts.filter(
        created_at__date__gte=week_start).values_list("created_at__date", flat=True))
    active_dates |= set(game_completions.filter(
        completed_at__date__gte=week_start).values_list("completed_at__date", flat=True))
    week_days = [
        {"label": (week_start + timedelta(days=i)).strftime("%a"),
         "done": (week_start + timedelta(days=i)) in active_dates,
         "is_today": (week_start + timedelta(days=i)) == today}
        for i in range(7)
    ]

    daily_done_today = DailyChallengeLog.objects.filter(
        user=request.user, date=today, completed=True).exists()

    due_revision = RevisionItem.objects.filter(
        user=request.user, mastered=False, next_review_date__lte=today).count()

    pending_assignments = Assignment.objects.exclude(
        completions__user=request.user).order_by("deadline")[:5]

    pending_challenges = FriendChallenge.objects.filter(
        opponent=request.user, status="pending")

    ctx = {
        "profile": profile,
        "level": level,
        "level_title": gamification.level_title(level),
        "next_level_title": gamification.level_title(level + 1),
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
        "xp_pct": xp_pct,
        "total_xp": profile.xp,
        "badges": badges,
        "completed_count": completed_count,
        "accuracy": accuracy,
        "week_days": week_days,
        "daily_done_today": daily_done_today,
        "due_revision": due_revision,
        "pending_assignments": pending_assignments,
        "pending_challenges": pending_challenges,
        "recommended_topic": Topic.objects.filter(
            slug=profile.recommended_topic_slug).first() if profile.recommended_topic_slug else None,
    }
    return render(request, "dashboard.html", ctx)


# ----------------------------------------------------------- assessment --
ASSESSMENT_QUESTION_COUNT = 8


@login_required(login_url="login_page")
def assessment_start(request):
    ensure_seeded()
    ids = quiz_engine.build_question_set(count=ASSESSMENT_QUESTION_COUNT)
    quiz_engine.start_quiz(request, ids, source="assessment")
    return redirect("assessment_play")


@login_required(login_url="login_page")
def assessment_play(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if quiz_engine.is_finished(request):
        if not quiz_engine.get_state(request):
            return redirect("assessment_start")
        result = quiz_engine.finish_quiz(request, profile, topic=None, bonus_xp=20)
        attempt = result["attempt"]

        weak_topic = _weakest_topic_for_attempt(attempt)
        profile.assessment_taken = True
        if weak_topic:
            profile.recommended_topic_slug = weak_topic.slug
            profile.current_topic = weak_topic.name
        profile.save()

        return render(request, "assessment_result.html", {
            "attempt": attempt, "result": result,
            "recommended_topic": weak_topic,
        })

    if request.method == "POST":
        quiz_engine.submit_answer(request, request.POST.get("choice"))
        return redirect("assessment_play")

    question = quiz_engine.current_question(request)
    idx, total = quiz_engine.progress(request)
    return render(request, "assessment_play.html", {
        "question": question, "options": _shuffled_options(question),
        "step": idx + 1, "total": total,
    })


def _weakest_topic_for_attempt(attempt):
    per_topic = {}
    for item in QuestionAttempt.objects.filter(quiz_attempt=attempt).select_related(
            "question__topic"):
        t = item.question.topic
        per_topic.setdefault(t, [0, 0])
        per_topic[t][1] += 1
        if item.correct:
            per_topic[t][0] += 1
    if not per_topic:
        return None
    return min(per_topic, key=lambda t: per_topic[t][0] / per_topic[t][1])


def _shuffled_options(question):
    opts = [(i + 1, opt) for i, opt in enumerate(question.options())]
    random.shuffle(opts)
    return opts


# --------------------------------------------------------- topic practice --
@login_required(login_url="login_page")
def practice_topics(request):
    ensure_seeded()
    groups = []
    for key, label in Topic.GROUP_CHOICES:
        topics = list(Topic.objects.filter(group=key))
        for t in topics:
            attempts = QuizAttempt.objects.filter(
                user=request.user, topic=t, source="practice")
            correct = sum(a.score for a in attempts)
            total = sum(a.total for a in attempts)
            t.accuracy = round(100 * correct / total) if total else None
        groups.append({"key": key, "label": label, "topics": topics})
    return render(request, "practice_topics.html", {"groups": groups})


@login_required(login_url="login_page")
def practice_quiz(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if not quiz_engine.get_state(request) or request.GET.get("restart"):
        ids = quiz_engine.build_question_set(topic=topic, count=5)
        quiz_engine.start_quiz(request, ids, source="practice", topic_id=topic.id)

    if quiz_engine.is_finished(request):
        result = quiz_engine.finish_quiz(request, profile, topic=topic)
        profile.current_topic = topic.name
        profile.save(update_fields=["current_topic"])
        return render(request, "quiz_result.html", {
            "topic": topic, "result": result, "back_url": reverse("practice_topics"),
        })

    if request.method == "POST":
        outcome = quiz_engine.submit_answer(request, request.POST.get("choice"))
        idx, total = quiz_engine.progress(request)
        return render(request, "quiz_question.html", {
            "topic": topic, "answered": True, "outcome": outcome,
            "step": idx, "total": total, "next_url": reverse("practice_quiz", args=[slug]),
        })

    question = quiz_engine.current_question(request)
    idx, total = quiz_engine.progress(request)
    return render(request, "quiz_question.html", {
        "topic": topic, "question": question, "options": _shuffled_options(question),
        "step": idx + 1, "total": total,
    })


# --------------------------------------------------------- daily challenge --
@login_required(login_url="login_page")
def daily_challenge(request):
    ensure_seeded()
    profile, _ = Profile.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    log, _ = DailyChallengeLog.objects.get_or_create(user=request.user, date=today)

    if log.completed:
        return render(request, "daily_done.html", {"log": log})

    if not quiz_engine.get_state(request):
        random.seed(f"{today.isoformat()}-{request.user.id}")
        ids = quiz_engine.build_question_set(count=3)
        random.seed()
        quiz_engine.start_quiz(request, ids, source="daily")

    if quiz_engine.is_finished(request):
        result = quiz_engine.finish_quiz(request, profile, topic=None, bonus_xp=30)
        log.completed = True
        log.xp_awarded = result["xp_gained"]
        log.save()
        return render(request, "quiz_result.html", {
            "result": result, "daily": True, "back_url": reverse("dashboard"),
        })

    if request.method == "POST":
        outcome = quiz_engine.submit_answer(request, request.POST.get("choice"))
        idx, total = quiz_engine.progress(request)
        return render(request, "quiz_question.html", {
            "daily": True, "answered": True, "outcome": outcome,
            "step": idx, "total": total, "next_url": reverse("daily_challenge"),
        })

    question = quiz_engine.current_question(request)
    idx, total = quiz_engine.progress(request)
    return render(request, "quiz_question.html", {
        "daily": True, "question": question, "options": _shuffled_options(question),
        "step": idx + 1, "total": total,
    })


# ------------------------------------------------------------ revision mode --
@login_required(login_url="login_page")
def revision_mode(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    today = timezone.localdate()

    if not quiz_engine.get_state(request):
        due_ids = list(RevisionItem.objects.filter(
            user=request.user, mastered=False, next_review_date__lte=today
        ).values_list("question_id", flat=True)[:8])
        if not due_ids:
            return render(request, "revision_empty.html")
        random.shuffle(due_ids)
        quiz_engine.start_quiz(request, due_ids, source="revision")

    if quiz_engine.is_finished(request):
        result = quiz_engine.finish_quiz(request, profile, topic=None)
        return render(request, "quiz_result.html", {
            "result": result, "revision": True, "back_url": reverse("dashboard"),
        })

    if request.method == "POST":
        outcome = quiz_engine.submit_answer(request, request.POST.get("choice"))
        idx, total = quiz_engine.progress(request)
        return render(request, "quiz_question.html", {
            "revision": True, "answered": True, "outcome": outcome,
            "step": idx, "total": total, "next_url": reverse("revision_mode"),
        })

    question = quiz_engine.current_question(request)
    idx, total = quiz_engine.progress(request)
    return render(request, "quiz_question.html", {
        "revision": True, "question": question, "options": _shuffled_options(question),
        "step": idx + 1, "total": total,
    })


# --------------------------------------------------------------- playground --
@login_required(login_url="login_page")
def playground_page(request):
    starter = request.GET.get("starter", "")
    project_slug = request.GET.get("project", "")
    return render(request, "playground.html", {
        "starter_code": starter, "project_slug": project_slug,
    })


@require_POST
@login_required(login_url="login_page")
def playground_run(request):
    code = request.POST.get("code", "")[:20000]
    stdin_text = request.POST.get("stdin", "")
    if not code.strip():
        return JsonResponse({"ok": False, "error": "Write some code first."})

    result = sandbox.run_python(code, stdin_text=stdin_text)
    explanation = sandbox.explain_error(result["error"]) if result["error"] else None

    return JsonResponse({
        "ok": True, "success": result["success"], "output": result["output"],
        "error": result["error"], "timed_out": result["timed_out"],
        "explanation": explanation,
    })


# ------------------------------------------------------- build-something-real
@login_required(login_url="login_page")
def projects_list(request):
    ensure_seeded()
    projects = list(Project.objects.all())
    done_ids = set(ProjectSubmission.objects.filter(
        user=request.user, completed=True).values_list("project_id", flat=True))
    for p in projects:
        p.done = p.id in done_ids
    return render(request, "projects_list.html", {"projects": projects})


@login_required(login_url="login_page")
def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    submission = ProjectSubmission.objects.filter(user=request.user, project=project).first()
    return render(request, "project_detail.html", {
        "project": project, "submission": submission,
    })


@require_POST
@login_required(login_url="login_page")
def project_submit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    code = request.POST.get("code", "")

    submission, created = ProjectSubmission.objects.get_or_create(
        user=request.user, project=project, defaults={"code": code})
    already_done = submission.completed
    submission.code = code
    submission.completed = True
    submission.save()

    result = None
    if not already_done:
        result = gamification.record_project_submission(request.user, profile, project)

    return render(request, "project_result.html", {
        "project": project, "result": result, "already_done": already_done,
    })


# --------------------------------------------------------------- analytics --
@login_required(login_url="login_page")
def analytics_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    attempts = QuizAttempt.objects.filter(user=request.user)

    breakdown = []
    for topic in Topic.objects.all():
        topic_attempts = attempts.filter(topic=topic)
        total = sum(a.total for a in topic_attempts)
        correct = sum(a.score for a in topic_attempts)
        if total:
            breakdown.append({"name": topic.name, "accuracy": round(100 * correct / total),
                               "questions": total})
    breakdown.sort(key=lambda b: b["accuracy"])

    total_q = sum(a.total for a in attempts) + sum(
        c.max_score // 10 for c in GameCompletion.objects.filter(user=request.user))
    total_correct = sum(a.score for a in attempts) + sum(
        c.score // 10 for c in GameCompletion.objects.filter(user=request.user))

    recent = list(attempts.order_by("-created_at")[:10])

    return render(request, "analytics.html", {
        "profile": profile, "breakdown": breakdown,
        "total_questions": total_q, "total_correct": total_correct,
        "overall_accuracy": round(100 * total_correct / total_q) if total_q else None,
        "recent": recent,
        "weakest": breakdown[0] if breakdown else None,
        "strongest": breakdown[-1] if breakdown else None,
    })


@login_required(login_url="login_page")
def ai_analysis_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    attempts = QuizAttempt.objects.filter(user=request.user)

    breakdown = []
    for topic in Topic.objects.all():
        topic_attempts = attempts.filter(topic=topic)
        total = sum(a.total for a in topic_attempts)
        correct = sum(a.score for a in topic_attempts)
        if total:
            breakdown.append({"name": topic.name, "accuracy": round(100 * correct / total)})
    breakdown.sort(key=lambda b: b["accuracy"])

    total_q = sum(a.total for a in attempts)
    total_correct = sum(a.score for a in attempts)

    stats = {
        "total_attempts": attempts.count(),
        "overall_accuracy": round(100 * total_correct / total_q) if total_q else 0,
        "streak": profile.streak,
        "strongest_topic": breakdown[-1]["name"] if breakdown else None,
        "weakest_topic": breakdown[0]["name"] if breakdown else None,
        "topic_breakdown": breakdown,
        "next_topic": profile.recommended_topic_slug,
    }

    analysis_text, recommended_name = ai_analysis.generate_analysis(stats)
    recommended_topic = Topic.objects.filter(name__iexact=recommended_name).first()

    return render(request, "ai_analysis.html", {
        "analysis_text": analysis_text, "stats": stats,
        "recommended_topic": recommended_topic, "recommended_name": recommended_name,
        "ai_configured": chatbot.is_configured(),
    })


# ------------------------------------------------------------------ friends --
@login_required(login_url="login_page")
def friends_page(request):
    from django.db.models import Q
    accepted = Friendship.objects.filter(status="accepted").filter(
        Q(from_user=request.user) | Q(to_user=request.user))
    friend_users = []
    for f in accepted:
        friend_users.append(f.to_user if f.from_user_id == request.user.id else f.from_user)

    incoming = Friendship.objects.filter(to_user=request.user, status="pending")
    sent_challenges = FriendChallenge.objects.filter(created_by=request.user)
    received_challenges = FriendChallenge.objects.filter(opponent=request.user)

    return render(request, "friends.html", {
        "friend_users": friend_users, "incoming": incoming,
        "sent_challenges": sent_challenges, "received_challenges": received_challenges,
        "topics": Topic.objects.all(),
    })


@require_POST
@login_required(login_url="login_page")
def friend_add(request):
    username = (request.POST.get("username") or "").strip()
    target = User.objects.filter(username__iexact=username).exclude(id=request.user.id).first()
    if target:
        Friendship.objects.get_or_create(from_user=request.user, to_user=target)
    return redirect("friends_page")


@require_POST
@login_required(login_url="login_page")
def friend_accept(request, friendship_id):
    fr = get_object_or_404(Friendship, id=friendship_id, to_user=request.user)
    fr.status = "accepted"
    fr.save()
    Friendship.objects.get_or_create(
        from_user=request.user, to_user=fr.from_user, defaults={"status": "accepted"})
    return redirect("friends_page")


@require_POST
@login_required(login_url="login_page")
def friend_challenge_create(request, user_id):
    opponent = get_object_or_404(User, id=user_id)
    topic_id = request.POST.get("topic_id") or None
    challenge = FriendChallenge.objects.create(
        created_by=request.user, opponent=opponent, topic_id=topic_id,
    )
    return redirect("friend_challenge_play", challenge_id=challenge.id)


@login_required(login_url="login_page")
def friend_challenge_play(request, challenge_id):
    challenge = get_object_or_404(FriendChallenge, id=challenge_id)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.user.id not in (challenge.created_by_id, challenge.opponent_id):
        return redirect("friends_page")

    is_creator = request.user.id == challenge.created_by_id
    my_attempt = challenge.creator_attempt if is_creator else challenge.opponent_attempt
    if my_attempt:
        return redirect("friend_challenge_result", challenge_id=challenge.id)

    if not quiz_engine.get_state(request) or request.session.get("fc_active_id") != challenge.id:
        ids = quiz_engine.build_question_set(topic=challenge.topic, count=5)
        quiz_engine.start_quiz(request, ids, source="friend_challenge",
                                topic_id=challenge.topic_id if challenge.topic_id else None)
        request.session["fc_active_id"] = challenge.id

    if quiz_engine.is_finished(request):
        result = quiz_engine.finish_quiz(request, profile, topic=challenge.topic, bonus_xp=10)
        if is_creator:
            challenge.creator_attempt = result["attempt"]
        else:
            challenge.opponent_attempt = result["attempt"]
        if challenge.creator_attempt and challenge.opponent_attempt:
            challenge.status = "completed"
        challenge.save()
        request.session.pop("fc_active_id", None)
        return redirect("friend_challenge_result", challenge_id=challenge.id)

    if request.method == "POST":
        outcome = quiz_engine.submit_answer(request, request.POST.get("choice"))
        idx, total = quiz_engine.progress(request)
        return render(request, "quiz_question.html", {
            "friend_challenge": challenge, "answered": True, "outcome": outcome,
            "step": idx, "total": total,
            "next_url": reverse("friend_challenge_play", args=[challenge.id]),
        })

    question = quiz_engine.current_question(request)
    idx, total = quiz_engine.progress(request)
    return render(request, "quiz_question.html", {
        "friend_challenge": challenge, "question": question,
        "options": _shuffled_options(question), "step": idx + 1, "total": total,
    })


@login_required(login_url="login_page")
def friend_challenge_result(request, challenge_id):
    challenge = get_object_or_404(FriendChallenge, id=challenge_id)
    if request.user.id not in (challenge.created_by_id, challenge.opponent_id):
        return redirect("friends_page")
    winner = challenge.winner()
    return render(request, "friend_challenge_result.html", {
        "challenge": challenge, "winner": winner,
    })


# ------------------------------------------------------------ teacher tools --
@login_required(login_url="login_page")
def teacher_dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_teacher:
        return redirect("dashboard")

    students = Profile.objects.filter(role="student").select_related("user")
    for s in students:
        attempts = QuizAttempt.objects.filter(user=s.user)
        total = sum(a.total for a in attempts)
        correct = sum(a.score for a in attempts)
        s.accuracy = round(100 * correct / total) if total else None

    topic_stats = []
    for topic in Topic.objects.all():
        items = QuestionAttempt.objects.filter(question__topic=topic)
        total = items.count()
        correct = items.filter(correct=True).count()
        if total:
            topic_stats.append({"name": topic.name, "accuracy": round(100 * correct / total),
                                 "attempts": total})
    topic_stats.sort(key=lambda t: t["accuracy"])
    weak_topics = topic_stats[:3]

    assignments = Assignment.objects.filter(teacher=request.user)

    return render(request, "teacher_dashboard.html", {
        "students": students, "weak_topics": weak_topics, "assignments": assignments,
        "topics": Topic.objects.all(),
    })


@require_POST
@login_required(login_url="login_page")
def teacher_assignment_create(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_teacher:
        return redirect("dashboard")

    Assignment.objects.create(
        teacher=request.user,
        title=(request.POST.get("title") or "Untitled assignment").strip(),
        instructions=request.POST.get("instructions", ""),
        topic_id=request.POST.get("topic_id") or None,
        deadline=request.POST.get("deadline") or None,
    )
    return redirect("teacher_dashboard")


@require_POST
@login_required(login_url="login_page")
def assignment_complete(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    AssignmentCompletion.objects.get_or_create(assignment=assignment, user=request.user)
    return redirect("dashboard")


# --------------------------------------------------------------- accessibility
@login_required(login_url="login_page")
def settings_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.theme_mode = request.POST.get("theme_mode", "dark")
        profile.font_size = request.POST.get("font_size", "medium")
        profile.reduce_motion = bool(request.POST.get("reduce_motion"))
        profile.density = request.POST.get("density", "comfortable")
        profile.display_name = request.POST.get("display_name", profile.display_name)[:80]
        profile.save()
        return redirect("settings_page")
    return render(request, "settings.html", {"profile": profile})


# --------------------------------------------------------- language / level --
def learn_start(request):
    return redirect("language_page")


def language_page(request):
    return render(request, "language.html", {"languages": data.LANGUAGES})


def set_language(request, code):
    if code in data.TR:
        request.session["lang"] = code
    return redirect("level_page")


def level_page(request):
    return render(request, "level.html")


def set_level(request, lvl):
    if lvl not in ("beginner", "intermediate", "advanced"):
        return redirect("level_page")
    request.session["level"] = lvl
    if lvl == "beginner":
        request.session["purpose"] = None
        return redirect("mode_page")
    return redirect("purpose_page")


def purpose_page(request):
    if request.session.get("level") not in ("intermediate", "advanced"):
        return redirect("level_page")
    return render(request, "purpose.html", {"purposes": data.PURPOSES})


def set_purpose(request, key):
    if key not in data.PURPOSES:
        return redirect("purpose_page")
    request.session["purpose"] = key
    return redirect("mode_page")


# -------------------------------------------------------------------- mode --
def mode_page(request):
    if not request.session.get("lang"):
        return redirect("language_page")
    if not request.session.get("level"):
        return redirect("level_page")
    return render(request, "mode.html")


# ------------------------------------------------------------- animation --
def animation_page(request):
    """Animation Mode video library: a grid of short animated lessons."""
    from .animation_data import LESSONS
    from .models import Topic

    group_labels = dict(Topic.GROUP_CHOICES)
    grouped = {}
    for lesson in LESSONS:
        topic = Topic.objects.filter(slug=lesson["topic_slug"]).first()
        group_key = topic.group if topic else "foundations"
        grouped.setdefault(group_key, []).append(lesson)

    # Keep a stable, sensible group order even if a group has no lessons yet.
    groups = []
    for key in ["foundations", "control_flow", "data_structures", "file_handling"]:
        if key in grouped:
            groups.append({"label": group_labels.get(key, key), "lessons": grouped[key]})

    return render(request, "animation_library.html", {"groups": groups})


def animation_lesson_view(request, slug):
    """One animated lesson. 'getting-started' is the original hand-built,
    5-language intro; every other slug is served by the generic step engine."""
    if slug == "getting-started":
        lang = request.session.get("lang", "en")
        keys = [
            "menu_back", "animation_mode_title", "back_btn", "continue_btn",
            "demo_prompt", "run_demo_btn",
            "anim_step1_label", "anim_step1_text", "bubble1", "bubble2", "bubble3",
            "anim_step2_label", "anim_step2_text",
            "anim_step3_label", "recipe_step1", "recipe_step2", "recipe_step3", "recipe_step4",
            "anim_algorithm_text",
            "anim_step4_label", "ipo_example_caption", "box_input", "box_process", "box_output",
            "ipo_explain_text",
            "anim_step5_label", "second_example_text", "atm_caption", "atm_input",
            "atm_process", "atm_output", "atm_explain_text",
            "anim_step6_label", "first_code_text", "code_explain_text",
            "anim_step7_label", "final_explain_text",
            "processing_text", "demo_output", "step_progress", "recipe_step_prefix",
        ]
        strings = {k: data.t(lang, k) for k in keys}
        return render(request, "animation_lesson_intro.html", {"strings_json": strings})

    from .animation_data import get_lesson
    from .models import Topic

    lesson = get_lesson(slug)
    if not lesson:
        return redirect("animation_page")

    topic = Topic.objects.filter(slug=lesson["topic_slug"]).first()
    return render(request, "animation_lesson.html", {
        "lesson": lesson, "steps_json": lesson["steps"], "topic": topic,
    })


# ---------------------------------------------------------------- theory --
def theory_page(request):
    ensure_seeded()
    lang = request.session.get("lang", "en")
    module_key = request.GET.get("m", data.MODULE_KEYS[0])
    if module_key not in data.MODULE_KEYS:
        module_key = data.MODULE_KEYS[0]
    notes = data.get_notes(lang, module_key)

    purpose_key = request.session.get("purpose")
    purpose_label = None
    if request.session.get("level") in ("intermediate", "advanced") and purpose_key:
        purpose_label = data.t(lang, data.PURPOSE_KEY_MAP[purpose_key])

    # Practice topics that belong to this module, so learners can jump
    # straight from the notes into a matching quiz.
    module_group_map = {
        "module1": "foundations",
        "module2": "control_flow",
        "module3": "data_structures",
        "module4": "file_handling",
    }
    related_topics = list(Topic.objects.filter(group=module_group_map.get(module_key, "")))

    modules = [
        {"key": key, "label": label, "icon": icon, "active": key == module_key}
        for key, label, icon in data.MODULES
    ]

    return render(request, "theory.html", {
        "notes": notes, "purpose_label": purpose_label,
        "modules": modules, "current_module": module_key,
        "related_topics": related_topics,
        "show_intro_quiz": module_key == "module1",
    })


# ----------------------------------------------------------------- game --
def _final_bits(request, score):
    score_line = _t(request, "final_score_template", score=score)
    score_line = score_line.replace("/30", "/{}".format(data.MAX_SCORE))
    if score == data.MAX_SCORE:
        msg = _t(request, "msg_perfect")
    elif score >= data.MAX_SCORE // 2:
        msg = _t(request, "msg_good")
    else:
        msg = _t(request, "msg_try")
    return score_line, msg


def _task1_options(request):
    opts = [
        {"value": "wrong", "label": _t(request, "task1_opt1")},
        {"value": "correct", "label": _t(request, "task1_opt2")},
        {"value": "wrong2", "label": _t(request, "task1_opt3")},
    ]
    random.shuffle(opts)
    return opts


def _vending_options(request):
    opts = [
        {"value": "input", "label": _t(request, "opt_input")},
        {"value": "process", "label": _t(request, "opt_process")},
        {"value": "output", "label": _t(request, "opt_output")},
    ]
    random.shuffle(opts)
    return opts


def _task_context(request):
    """Builds the context needed to show whichever task is currently active."""
    idx = request.session.get("task_index", 0)
    task = data.GAME_TASKS[idx]
    ctx = {
        "finished": False, "task": task,
        "score": request.session.get("score", 0),
        "streak": request.session.get("streak", 0),
        "task_number": idx + 1,
        "task_total": len(data.GAME_TASKS),
        "progress_pct": int(idx / len(data.GAME_TASKS) * 100),
    }
    if task == "task1":
        ctx["options"] = _task1_options(request)
    elif task in ("task2a", "task2b", "task2c"):
        desc_key = {"task2a": "vending_press", "task2b": "vending_check", "task2c": "vending_drop"}[task]
        ctx["vending_desc"] = _t(request, desc_key)
        ctx["options"] = _vending_options(request)
    return ctx


def _pop_level_up_info(request):
    """Pulled once (and only once) from the session so a 'Level up!' /
    'New badge!' callout shows on the results screen exactly once."""
    return request.session.pop("level_up_info", None)


def game_page(request):
    if "score" not in request.session or request.GET.get("restart"):
        request.session["score"] = 0
        request.session["task_index"] = 0
        request.session["streak"] = 0
        request.session["best_streak"] = 0
        request.session.pop("level_up_info", None)
    idx = request.session.get("task_index", 0)
    if idx >= len(data.GAME_TASKS):
        score_line, msg = _final_bits(request, request.session["score"])
        return render(request, "game.html", {
            "finished": True, "score": request.session["score"],
            "score_line": score_line, "final_msg": msg,
            "best_streak": request.session.get("best_streak", 0),
            "task_total": len(data.GAME_TASKS),
            "level_up_info": _pop_level_up_info(request),
        })
    return render(request, "game.html", _task_context(request))


def game_answer(request):
    idx = request.session.get("task_index", 0)
    if idx >= len(data.GAME_TASKS):
        return redirect("game_page")

    task = data.GAME_TASKS[idx]
    correct = False
    feedback_correct = feedback_wrong = ""

    if task == "task1":
        choice = request.POST.get("choice")
        correct = choice == "correct"
        feedback_correct, feedback_wrong = _t(request, "task1_fb_correct"), _t(request, "task1_fb_wrong")
    elif task in ("task2a", "task2b", "task2c"):
        answer_map = {"task2a": "input", "task2b": "process", "task2c": "output"}
        expected = answer_map[task]
        guess = request.POST.get("guess")
        correct = guess == expected
        label = _t(request, {"input": "opt_input", "process": "opt_process",
                              "output": "opt_output"}[expected]).upper()
        feedback_correct = _t(request, "vending_correct", label=label)
        feedback_wrong = _t(request, "vending_wrong", label=label)
    elif task == "task3":
        value = request.POST.get("value", "")
        try:
            n = float(value)
            result = n * 2
            if result == int(result):
                result = int(result)
            if n == int(n):
                n = int(n)
            correct = True
            feedback_correct = _t(request, "task3_output_template", n=n, result=result)
        except ValueError:
            feedback_wrong = _t(request, "task3_invalid")

    if correct:
        request.session["score"] = request.session.get("score", 0) + 10
        request.session["streak"] = request.session.get("streak", 0) + 1
        request.session["best_streak"] = max(request.session.get("best_streak", 0),
                                              request.session["streak"])
    else:
        request.session["streak"] = 0

    request.session["task_index"] = idx + 1
    request.session.modified = True

    just_finished = (idx + 1) >= len(data.GAME_TASKS)
    level_up_info = None
    if just_finished and request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        level_up_info = gamification.record_game_completion(
            user=request.user, profile=profile,
            score=request.session.get("score", 0), max_score=data.MAX_SCORE,
        )
        request.session["level_up_info"] = {
            "leveled_up": level_up_info["leveled_up"],
            "new_level": level_up_info["new_level"],
            "new_badges": [b.name for b in level_up_info["new_badges"]],
        }

    return render(request, "game.html", {
        "finished": False, "task": task, "answered": True, "correct": correct,
        "feedback": feedback_correct if correct else feedback_wrong,
        "score": request.session.get("score", 0),
        "streak": request.session.get("streak", 0),
        "task_number": idx + 1,
        "task_total": len(data.GAME_TASKS),
        "progress_pct": int((idx + 1) / len(data.GAME_TASKS) * 100),
        "next_url": reverse("game_next"),
    })


def game_next(request):
    idx = request.session.get("task_index", 0)
    if idx >= len(data.GAME_TASKS):
        score_line, msg = _final_bits(request, request.session.get("score", 0))
        return render(request, "game.html", {
            "finished": True, "score": request.session.get("score", 0),
            "score_line": score_line, "final_msg": msg,
            "best_streak": request.session.get("best_streak", 0),
            "task_total": len(data.GAME_TASKS),
            "level_up_info": _pop_level_up_info(request),
        })
    return render(request, "game.html", _task_context(request))


# --------------------------------------------------------- Algoria tutor chat --
CHAT_HISTORY_SESSION_KEY = "chat_history"


@require_POST
def chat_send(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Bad request.", "kind": "api_error"}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"ok": False, "error": "Type a question first.", "kind": "api_error"}, status=400)
    if len(message) > 2000:
        message = message[:2000]

    history = request.session.get(CHAT_HISTORY_SESSION_KEY, [])
    history = history + [{"role": "user", "content": message}]

    lang = request.session.get("lang", "en")
    lang_label = dict(data.LANGUAGES).get(lang, "English").split(" (")[0]
    level = request.session.get("level")
    purpose = request.session.get("purpose")

    ok, reply, kind = chatbot.ask_algoria(history, lang_label=lang_label, level=level, purpose=purpose)

    if ok:
        history = history + [{"role": "assistant", "content": reply}]
        request.session[CHAT_HISTORY_SESSION_KEY] = history[-chatbot.MAX_HISTORY_MESSAGES:]
        request.session.modified = True
        return JsonResponse({"ok": True, "reply": reply})

    # Don't persist the failed turn's user message as part of the remembered history,
    # so the learner can just retry without a lingering unanswered message in context.
    return JsonResponse({"ok": False, "error": reply, "kind": kind}, status=200)


def chat_reset(request):
    request.session[CHAT_HISTORY_SESSION_KEY] = []
    request.session.modified = True
    return JsonResponse({"ok": True})
