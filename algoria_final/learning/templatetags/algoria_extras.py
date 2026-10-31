import json
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .. import data as appdata

register = template.Library()


@register.filter
def format_analysis(text):
    """Escapes the AI analysis text, then turns **bold** into <strong> and
    line breaks into <br> — just enough formatting for a short paragraph."""
    if not text:
        return ""
    safe = escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = safe.replace("\n", "<br>")
    return mark_safe(safe)


@register.simple_tag(takes_context=True)
def t(context, key, **kwargs):
    """Usage: {% t 'some_key' %} or {% t 'tpl_key' name=value %} or
    {% t 'key' as my_var %} to capture the result in a template variable."""
    request = context.get("request")
    lang = request.session.get("lang", "en") if request else "en"
    return appdata.t(lang, key, **kwargs)


@register.filter
def to_json(value):
    return json.dumps(value)
