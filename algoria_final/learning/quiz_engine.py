"""
Generic quiz engine shared by Topic Practice, the Daily Challenge, the
Placement Assessment, Smart Revision and Friend Challenges. One question
at a time, session-tracked, same feedback pattern as the existing Game
Mode ("never just say wrong — always explain why").
"""

import random
from datetime import timedelta

from django.utils import timezone

from . import gamification
from .models import Question, QuestionAttempt, RevisionItem

SESSION_KEY = "quiz_state"


def start_quiz(request, question_ids, source, topic_id=None, extra=None):
    request.session[SESSION_KEY] = {
        "source": source,
        "topic_id": topic_id,
        "question_ids": list(question_ids),
        "index": 0,
        "correct": 0,
        "answered_ids": [],
        "extra": extra or {},
    }
    request.session.modified = True


def get_state(request):
    return request.session.get(SESSION_KEY)


def clear(request):
    request.session.pop(SESSION_KEY, None)


def is_finished(request):
    state = get_state(request)
    if not state:
        return True
    return state["index"] >= len(state["question_ids"])


def current_question(request):
    state = get_state(request)
    if not state or is_finished(request):
        return None
    qid = state["question_ids"][state["index"]]
    return Question.objects.get(pk=qid)


def progress(request):
    state = get_state(request)
    if not state:
        return 0, 0
    return state["index"], len(state["question_ids"])


def submit_answer(request, chosen_option):
    """Record the answer for the current question. Returns a dict with
    correct/question/explanation. Advances the pointer."""
    state = get_state(request)
    question = current_question(request)
    correct = question.is_correct(chosen_option)

    state["answered_ids"].append({"question_id": question.id, "chosen": int(chosen_option),
                                   "correct": correct})
    if correct:
        state["correct"] += 1
    state["index"] += 1
    request.session[SESSION_KEY] = state
    request.session.modified = True

    _update_revision_item(request.user, question, correct)

    return {
        "correct": correct, "question": question,
        "explanation": question.explanation,
    }


def _update_revision_item(user, question, correct):
    if not user.is_authenticated:
        return
    today = timezone.localdate()
    if correct:
        try:
            item = RevisionItem.objects.get(user=user, question=question)
        except RevisionItem.DoesNotExist:
            return
        if item.times_missed <= 1:
            item.mastered = True
        else:
            item.times_missed -= 1
            item.next_review_date = today + timedelta(days=3)
        item.save()
    else:
        item, _ = RevisionItem.objects.get_or_create(
            user=user, question=question,
            defaults={"next_review_date": today + timedelta(days=1)},
        )
        if item.pk and item.times_missed:
            item.times_missed += 1
        item.mastered = False
        item.next_review_date = today + timedelta(days=1)
        item.save()


def finish_quiz(request, profile, topic=None, bonus_xp=0):
    """Finalize the quiz: award XP/streak/badges, log per-question results,
    clear session state. Returns the gamification result dict plus the
    QuizAttempt."""
    state = get_state(request)
    source = state["source"]
    correct = state["correct"]
    total = len(state["question_ids"])

    result = gamification.record_quiz_attempt(
        user=request.user, profile=profile, topic=topic, source=source,
        score=correct, total=total, bonus_xp=bonus_xp,
    )
    attempt = result["attempt"]

    for item in state["answered_ids"]:
        QuestionAttempt.objects.create(
            quiz_attempt=attempt, question_id=item["question_id"],
            chosen_option=item["chosen"], correct=item["correct"],
        )

    clear(request)
    return result


def build_question_set(topic=None, count=5, difficulty_pool=None):
    """Pick `count` random questions, optionally restricted to a topic
    and/or difficulty list."""
    qs = Question.objects.all()
    if topic is not None:
        qs = qs.filter(topic=topic)
    if difficulty_pool:
        qs = qs.filter(difficulty__in=difficulty_pool)
    ids = list(qs.values_list("id", flat=True))
    random.shuffle(ids)
    return ids[:count]
