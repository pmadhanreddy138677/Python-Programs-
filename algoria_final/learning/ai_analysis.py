"""
🤖 AI ANALYSIS step of the personalized learning pipeline
(PROFILE → ASSESSMENT → PATH → LEARN/PRACTICE/CODE → CHALLENGE → PROJECT →
PERFORMANCE → AI ANALYSIS → NEXT RECOMMENDATION).

Turns a student's stats into a short, encouraging analysis and a concrete
next-topic recommendation. Uses Claude when ANTHROPIC_API_KEY is set;
otherwise falls back to a simple rule-based analysis so the feature keeps
working offline (see design principle: the app must work without a key).
"""

import os

from . import chatbot

DEFAULT_MODEL = os.environ.get("ALGORIA_CHAT_MODEL", "claude-sonnet-5")


def _fallback_analysis(stats):
    weak = stats["weakest_topic"]
    strong = stats["strongest_topic"]
    lines = []
    lines.append(
        f"You've completed {stats['total_attempts']} challenges with "
        f"{stats['overall_accuracy']}% overall accuracy — nice work staying consistent."
    )
    if strong:
        lines.append(f"You're strongest in **{strong}** — that's a good foundation to build on.")
    if weak:
        lines.append(
            f"**{weak}** looks like it needs a bit more practice — a short focused "
            f"session there would help the most right now."
        )
    if stats["streak"] >= 3:
        lines.append(f"Your {stats['streak']}-day streak is helping this stick — keep it up!")
    recommendation = weak or stats.get("next_topic") or "the next topic in your path"
    lines.append(f"Recommended next step: practice **{recommendation}**.")
    return "\n\n".join(lines), recommendation


def generate_analysis(stats):
    """
    stats: dict with keys total_attempts, overall_accuracy, streak,
           strongest_topic, weakest_topic, topic_breakdown (list of
           {"name","accuracy"}), next_topic.

    Returns (analysis_text, recommended_topic_name).
    """
    if not chatbot.is_configured():
        return _fallback_analysis(stats)

    try:
        import anthropic
    except ImportError:
        return _fallback_analysis(stats)

    breakdown_lines = "\n".join(
        f"- {t['name']}: {t['accuracy']}% accuracy" for t in stats["topic_breakdown"]
    ) or "- No topic data yet."

    prompt = (
        "You are Algoria's learning analyst. Given this student's stats, write a short "
        "(3-4 sentence), warm, encouraging performance analysis for a beginner "
        "programming student, then on a new final line write exactly:\n"
        "RECOMMEND: <one topic name from the list below>\n\n"
        f"Total challenges completed: {stats['total_attempts']}\n"
        f"Overall accuracy: {stats['overall_accuracy']}%\n"
        f"Current streak: {stats['streak']} days\n"
        f"Per-topic accuracy:\n{breakdown_lines}\n\n"
        "Keep it specific to the numbers above, never invent topics not listed, and "
        "recommend whichever topic most needs practice (lowest accuracy, or the "
        "listed next topic if there isn't enough data yet)."
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=DEFAULT_MODEL, max_tokens=350,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not text:
            return _fallback_analysis(stats)

        recommendation = stats.get("weakest_topic") or stats.get("next_topic") or ""
        if "RECOMMEND:" in text:
            body, rec_line = text.rsplit("RECOMMEND:", 1)
            text = body.strip()
            recommendation = rec_line.strip() or recommendation
        return text, recommendation
    except Exception:
        return _fallback_analysis(stats)
