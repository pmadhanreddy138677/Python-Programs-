"""
The Algoria tutor chatbot.

A small wrapper around the Anthropic API that turns Claude into "Algoria" —
a friendly, patient Python tutor embedded in the site. Kept in its own
module so the chat logic (prompt building, history trimming, error
handling) stays separate from ordinary page views.

Requires the person running this site to set an ANTHROPIC_API_KEY
environment variable with their own Anthropic API key. If it's not set,
`ask_algoria` returns a clear "not configured" result instead of crashing.
"""

import os

MAX_HISTORY_MESSAGES = 16          # keep the last N messages (user+assistant) for context
MAX_REPLY_TOKENS = 700             # keep answers short and example-driven, not essays
DEFAULT_MODEL = os.environ.get("ALGORIA_CHAT_MODEL", "claude-sonnet-5")

LEVEL_LABELS = {
    "beginner": "a complete beginner",
    "intermediate": "an intermediate learner who knows the basics",
    "advanced": "an advanced learner preparing for real-world use",
}

PURPOSE_LABELS = {
    "college": "college / academic studies",
    "webdev": "web development",
    "gamedev": "game development",
    "job": "general job readiness",
    "interview": "technical interview preparation",
}


def _system_prompt(lang_label, level, purpose):
    lines = [
        "You are Algoria, the friendly built-in Python tutor for the Algoria learning "
        "website. You help learners understand programming concepts and clear up their "
        "doubts about Python.",
        "",
        "How you teach:",
        "- Always explain with short, everyday, easy-to-follow examples before (or instead "
        "of) technical jargon.",
        "- Keep answers concise — a few short paragraphs or a short code snippet at most. "
        "You are a chat tutor, not a textbook.",
        "- When showing code, keep it minimal and runnable, and briefly say what it does.",
        "- If a question is vague, give your best helpful answer first, then ask at most one "
        "short follow-up question if it would genuinely help.",
        "- Be warm and encouraging, especially with mistakes — normalize not knowing "
        "something yet.",
        "- Stay focused on Python, programming fundamentals, and this site's lessons "
        "(Animation Mode, Theory & Practice, Game Mode). For unrelated topics, gently steer "
        "back to what you can help with here.",
    ]
    if level:
        lines.append(f"- This learner is {LEVEL_LABELS.get(level, level)}; pitch your "
                      f"explanations at that level.")
    if purpose:
        lines.append(f"- They're learning for {PURPOSE_LABELS.get(purpose, purpose)}; "
                      f"prefer examples relevant to that when it fits naturally.")
    if lang_label and lang_label != "English":
        lines.append(f"- Their interface language is {lang_label}. If they write to you in "
                      f"that language, reply in that language. Otherwise, reply in whatever "
                      f"language they use. Python code itself always stays in English.")
    return "\n".join(lines)


def is_configured():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def ask_algoria(history, lang_label=None, level=None, purpose=None):
    """
    history: list of {"role": "user"|"assistant", "content": str}, ending with the
             newest user message.
    Returns (ok: bool, reply_or_error: str, error_kind: str|None)
    """
    if not is_configured():
        return False, (
            "The Algoria tutor chat isn't set up yet on this site — it needs an "
            "ANTHROPIC_API_KEY. See the README for a 2-minute setup."
        ), "not_configured"

    trimmed = history[-MAX_HISTORY_MESSAGES:]

    try:
        import anthropic
    except ImportError:
        return False, (
            "The 'anthropic' package isn't installed. Run "
            "`pip install -r requirements.txt` and try again."
        ), "not_configured"

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=MAX_REPLY_TOKENS,
            system=_system_prompt(lang_label, level, purpose),
            messages=[{"role": m["role"], "content": m["content"]} for m in trimmed],
        )
        reply_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not reply_text:
            return False, "Algoria didn't have anything to say — try asking again.", "api_error"
        return True, reply_text, None

    except anthropic.AuthenticationError:
        return False, (
            "Algoria couldn't log in to Anthropic — double-check your ANTHROPIC_API_KEY."
        ), "not_configured"
    except anthropic.RateLimitError:
        return False, "Algoria is a little busy right now — please try again in a moment.", "api_error"
    except anthropic.APIStatusError as e:
        return False, f"Algoria hit a snag talking to the API (status {e.status_code}). Please try again.", "api_error"
    except Exception:
        return False, "Something went wrong reaching Algoria. Please try again in a moment.", "api_error"
