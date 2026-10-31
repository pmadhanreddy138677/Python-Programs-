"""XP curve, level titles, streaks and badge-unlock logic.

Kept in one place (see the design brief: "Do not make XP too complicated")
so every activity — legacy Game Mode, topic practice, daily challenge,
projects, friend challenges — awards XP and streak credit the same way.
"""

from datetime import timedelta

from django.utils import timezone

from .models import Badge, GameCompletion, ProjectSubmission, QuizAttempt, UserBadge

LEVEL_TITLES = {
    1: "Beginner", 2: "Explorer", 3: "Learner", 4: "Problem Solver",
    5: "Code Warrior", 6: "Code Adventurer", 7: "Algorithm Ace",
    8: "Logic Architect", 9: "Python Pro", 10: "Algoria Master",
}


def level_title(level):
    if level in LEVEL_TITLES:
        return LEVEL_TITLES[level]
    return "Algoria Legend" if level > 10 else "Beginner"


def xp_for_level(level):
    """XP required to go from `level` to `level + 1`."""
    return 100 + (level - 1) * 50


def level_progress(total_xp):
    """Given a lifetime XP total, return (level, xp_into_level, xp_needed_for_next)."""
    level = 1
    remaining = total_xp
    while remaining >= xp_for_level(level):
        remaining -= xp_for_level(level)
        level += 1
    return level, remaining, xp_for_level(level)


# ---------------------------------------------------------------- badges --
BADGE_DEFS = [
    dict(slug="first_steps", name="First Steps", icon="🐣", sort_order=1,
         description="Complete your first challenge."),
    dict(slug="perfect_round", name="Perfect Round", icon="⭐", sort_order=2,
         description="Finish any quiz with a perfect score."),
    dict(slug="dedicated_learner", name="Dedicated Learner", icon="🎯", sort_order=3,
         description="Complete 10 challenges."),
    dict(slug="streak_master", name="Streak Master", icon="🔥", sort_order=4,
         description="Reach a 7-day learning streak."),
    dict(slug="code_warrior", name="Code Warrior", icon="🏆", sort_order=5,
         description="Reach Level 5."),
    dict(slug="topic_explorer", name="Topic Explorer", icon="🧭", sort_order=6,
         description="Practice questions from 3 different topics."),
    dict(slug="revision_pro", name="Revision Pro", icon="🧠", sort_order=7,
         description="Clear 10 questions in Smart Revision Mode."),
    dict(slug="project_builder", name="Project Builder", icon="🛠️", sort_order=8,
         description="Submit a 'Build Something Real' project."),
    dict(slug="challenge_champ", name="Challenge Champ", icon="🥇", sort_order=9,
         description="Win a Friend Challenge."),
]


def sync_badge_definitions():
    for d in BADGE_DEFS:
        Badge.objects.update_or_create(
            slug=d["slug"],
            defaults={"name": d["name"], "icon": d["icon"],
                      "description": d["description"], "sort_order": d["sort_order"]},
        )


def _award_badge(user, slug):
    try:
        badge = Badge.objects.get(slug=slug)
    except Badge.DoesNotExist:
        return None
    _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return badge if created else None


def check_and_award_badges(user, profile):
    """Look at the student's current stats and award any newly-earned
    badges. Returns the list of Badge objects unlocked just now."""
    from .models import RevisionItem  # local import avoids a circular import at module load

    newly = []
    game_completions = GameCompletion.objects.filter(user=user)
    quiz_attempts = QuizAttempt.objects.filter(user=user)
    total_completed = game_completions.count() + quiz_attempts.count()

    def give(slug):
        b = _award_badge(user, slug)
        if b:
            newly.append(b)

    if total_completed >= 1:
        give("first_steps")

    if any(c.is_perfect for c in game_completions[:50]) or \
            any(a.total and a.score == a.total for a in quiz_attempts[:50]):
        give("perfect_round")

    if total_completed >= 10:
        give("dedicated_learner")

    if profile.best_streak >= 7:
        give("streak_master")

    if profile.level >= 5:
        give("code_warrior")

    topics_practiced = quiz_attempts.filter(source="practice").values_list(
        "topic_id", flat=True).distinct().count()
    if topics_practiced >= 3:
        give("topic_explorer")

    if RevisionItem.objects.filter(user=user, mastered=True).count() >= 10:
        give("revision_pro")

    if ProjectSubmission.objects.filter(user=user, completed=True).exists():
        give("project_builder")

    from django.db.models import Q
    from .models import FriendChallenge
    completed_challenges = FriendChallenge.objects.filter(status="completed").filter(
        Q(created_by=user) | Q(opponent=user)
    )
    wins = sum(1 for fc in completed_challenges if fc.winner() == user)
    if wins >= 1:
        give("challenge_champ")

    return newly


# --------------------------------------------------------------- streaks --
def _update_streak(profile, friendly_message_target=None):
    """Advance the streak for 'today'. Uses one streak-freeze charge to
    protect a single missed day per week instead of resetting to zero —
    the streak should never feel punishing.

    Returns a short, kind status message describing what happened.
    """
    today = timezone.localdate()

    # Refill one freeze charge at the start of each new ISO week.
    monday = today - timedelta(days=today.weekday())
    if profile.freeze_refill_week != monday:
        profile.freeze_refill_week = monday
        profile.streak_freeze_charges = 1

    last = profile.last_activity_date
    message = None

    if last == today:
        message = None  # already counted today, nothing changes
    elif last == today - timedelta(days=1):
        profile.streak += 1
        message = f"🔥 {profile.streak}-day streak! Keep it going."
    elif last == today - timedelta(days=2) and profile.streak_freeze_charges > 0:
        profile.streak_freeze_charges -= 1
        profile.streak += 1
        message = "🧊 Streak freeze used — no worries, your learning journey continues!"
    else:
        if profile.streak > 0:
            message = "No worries! Your learning journey continues. New streak started today."
        profile.streak = 1

    profile.last_activity_date = today
    profile.best_streak = max(profile.best_streak, profile.streak)
    return message


# ------------------------------------------------------------ XP helpers --
def award_xp(profile, amount):
    """Add XP to a profile and keep its cached level in sync. Returns
    (leveled_up, new_level)."""
    old_level, _, _ = level_progress(profile.xp)
    profile.xp += amount
    new_level, _, _ = level_progress(profile.xp)
    profile.level = new_level
    return new_level > old_level, new_level


def record_game_completion(user, profile, score, max_score, topic=None):
    """Call once when a student finishes the legacy 5-task Game Mode round."""
    topic = topic or profile.current_topic
    leveled_up, new_level = award_xp(profile, score)
    streak_message = _update_streak(profile)
    profile.save()

    GameCompletion.objects.create(
        user=user, topic=topic, score=score, max_score=max_score, xp_awarded=score,
    )

    sync_badge_definitions()
    new_badges = check_and_award_badges(user, profile)

    return {
        "xp_gained": score, "leveled_up": leveled_up, "new_level": new_level,
        "new_badges": new_badges, "streak_message": streak_message,
    }


def record_quiz_attempt(user, profile, topic, source, score, total, bonus_xp=0):
    """Call once when a student finishes any quiz-engine round (topic
    practice, daily challenge, placement assessment, smart revision,
    friend challenge). XP = 10 per correct answer + any flat bonus."""
    xp_gained = score * 10 + bonus_xp
    leveled_up, new_level = award_xp(profile, xp_gained)
    streak_message = _update_streak(profile)
    profile.save()

    attempt = QuizAttempt.objects.create(
        user=user, topic=topic, source=source, score=score, total=total,
        xp_awarded=xp_gained,
    )

    sync_badge_definitions()
    new_badges = check_and_award_badges(user, profile)

    return {
        "attempt": attempt, "xp_gained": xp_gained, "leveled_up": leveled_up,
        "new_level": new_level, "new_badges": new_badges, "streak_message": streak_message,
    }


def record_project_submission(user, profile, project):
    leveled_up, new_level = award_xp(profile, project.xp_reward)
    streak_message = _update_streak(profile)
    profile.save()

    sync_badge_definitions()
    new_badges = check_and_award_badges(user, profile)

    return {
        "xp_gained": project.xp_reward, "leveled_up": leveled_up, "new_level": new_level,
        "new_badges": new_badges, "streak_message": streak_message,
    }
