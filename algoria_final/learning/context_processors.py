from functools import partial
import json

from django.middleware.csrf import get_token

from . import data


def algoria_globals(request):
    lang = request.session.get("lang", "en")
    level = request.session.get("level")
    purpose = request.session.get("purpose")
    lang_map = dict(data.LANGUAGES)
    get_token(request)  # ensures the CSRF cookie is set so the chat widget can read it
    chat_history = request.session.get("chat_history", [])

    profile = None
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)

    return {
        "t": partial(data.t, lang),
        "lang": lang if request.session.get("lang") else None,
        "lang_label": lang_map.get(lang, ""),
        "level": level,
        "purpose": purpose,
        "languages": data.LANGUAGES,
        "chat_history_json": json.dumps(chat_history),
        "profile": profile,
    }
