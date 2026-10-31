"""
Loads the multilingual UI strings + theory notes that power every learner-
facing page (language screen onward). Same data file used by the previous
Flask edition, so wording is identical across both.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "algoria_data.json", encoding="utf-8") as f:
    _DATA = json.load(f)

TR = _DATA["TR"]
NOTES = _DATA["NOTES"]

# Four learning modules shown as tabs on the Theory & Notes page. Every
# module has full English notes; other languages currently cover Module 1
# and fall back to English for Modules 2-4 (see `get_notes` below).
MODULES = [
    ("module1", "Module 1 · Python Fundamentals", "🐍"),
    ("module2", "Module 2 · Control Flow & Functions", "🔀"),
    ("module3", "Module 3 · Data Structures", "📦"),
    ("module4", "Module 4 · File & Exception Handling", "📁"),
]
MODULE_KEYS = [key for key, _, _ in MODULES]


def get_notes(lang, module_key):
    """Notes text for a module in `lang`, falling back to English if that
    language doesn't have this module yet, then to Module 1 as a last resort."""
    if module_key not in MODULE_KEYS:
        module_key = MODULE_KEYS[0]
    lang_notes = NOTES.get(lang, NOTES["en"])
    en_notes = NOTES["en"]
    return lang_notes.get(module_key) or en_notes.get(module_key) or en_notes["module1"]

LANGUAGES = [
    ("en", "English"),
    ("hi", "हिन्दी (Hindi)"),
    ("te", "తెలుగు (Telugu)"),
    ("gu", "ગુજરાતી (Gujarati)"),
    ("mr", "मराठी (Marathi)"),
]

PURPOSES = ["college", "webdev", "gamedev", "job", "interview"]

GAME_TASKS = ["task1", "task2a", "task2b", "task2c", "task3"]

MAX_SCORE = len(GAME_TASKS) * 10  # 5 tasks worth 10 points each

PURPOSE_KEY_MAP = {
    "college": "purpose_college",
    "webdev": "purpose_webdev",
    "gamedev": "purpose_gamedev",
    "job": "purpose_job",
    "interview": "purpose_interview",
}


def t(lang, key, **kwargs):
    """Translate `key` into `lang`, falling back to English, then the key itself."""
    text = TR.get(lang, TR["en"]).get(key, TR["en"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
