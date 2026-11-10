"""Facts for the model to answer from.

Pattern: a skill's ordered block notes the authored text that applies to this member (it picks the
response variant that the engine would send). The block sends nothing. The model then answers the
member's exact question from the skill's facts tool, which returns that text. The authored text
stays the single source of every figure, and the model can answer a follow-up question from it.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from rasa.mantle.content.responses import ResponseRegistry

TIMEZONE = ZoneInfo("America/New_York")

# `session.<namespace>.<entry>` in a condition, and `{session.<ns>.<entry>}` or `{entry}` placeholders.
_MEMORY_REF = re.compile(r"session\.([A-Za-z_]\w*\.[A-Za-z_]\w*)")
_TEMPLATE_FIELD = re.compile(r"\{session\.([^}]+)\}|\{([A-Za-z_]\w*)\}")

# The skill memory entry that holds the noted texts. Every skill that notes texts declares it.
NOTES_FIELD = "authored_texts"


def today_iso() -> str:
    return datetime.now(TIMEZONE).date().isoformat()


def us_date(value: date | str) -> str:
    """`2026-12-01` -> `December 1, 2026`."""
    day = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{day:%B} {day.day}, {day.year}"


# Memory keys that the opener's questions write. A member message that wrote one of them was an
# answer to the opener, not the question that the current skill must answer.
_OPENER_ANSWERS = ("initialize_conversation.membership_reply", "initialize_conversation.plan_reply")


def current_question(context: Any) -> str | None:
    """The question that the current skill must answer.

    Normally the member's latest typed message. When that message answered one of the opener's
    questions, the question is the request that the opener parked (`project.pending_request`).
    A `/command` and a button `set:` payload are not questions.
    """
    answered_opener = False
    for event in reversed(context.events):
        kind = type(event).__name__
        if kind == "MemorySet" and getattr(event, "key", None) in _OPENER_ANSWERS:
            answered_opener = True
            continue
        if kind != "UserUttered":
            continue
        text = (getattr(event, "text", "") or "").strip()
        if answered_opener or text.startswith("set:"):
            parked = context.memory.get("project.pending_request")
            if parked:
                return str(parked)
        if text and not text.startswith(("/", "set:")):
            return text
        answered_opener = False
    return None


class AuthoredTexts:
    """The authored responses of one skill, then of the project.

    Create it at import, `TEXTS = AuthoredTexts(Path(__file__).parent)`: the engine unpacks the model
    into a temporary folder, which may be gone when a tool runs.
    """

    def __init__(self, skill_dir: Path) -> None:
        paths = (skill_dir / "responses.yml", skill_dir.parent.parent / "responses.yml")
        self._registries = [ResponseRegistry.from_yaml(path) for path in paths if path.exists()]

    def variant_text(self, response: str, context: Any) -> str | None:
        """The variant of `response` that the engine would send now, with placeholders filled.
        None when no variant applies."""
        for registry in self._registries:
            if response not in registry.responses:
                continue
            variants = registry.responses[response].variants
            keys = {key for variant in variants for key in _MEMORY_REF.findall(variant.condition or "")}
            variant = registry.select_variant(response, {key: context.memory.get(key) for key in keys})
            return _fill(variant.text, context) if variant is not None else None
        return None


def _fill(template: str, context: Any) -> str:
    def _lookup(match: re.Match[str]) -> str:
        found = context.memory.get(match.group(1) or match.group(2))
        return match.group(0) if found is None else str(found)

    return _TEMPLATE_FIELD.sub(_lookup, template)


def note_authored(context: Any, texts: AuthoredTexts, response: str) -> None:
    """Add the text of `response` for this member to the noted texts, once."""
    text = texts.variant_text(response, context)
    noted = list(context.memory.get(NOTES_FIELD) or [])
    if text and all(entry["text"] != text for entry in noted):
        context.memory.set(NOTES_FIELD, [*noted, {"topic": response.removeprefix("utter_"), "text": text}])


def authored_notes(context: Any) -> list[dict[str, str]] | None:
    return context.memory.get(NOTES_FIELD) or None


def facts_payload(context: Any, **values: Any) -> dict[str, Any]:
    """A facts tool's result: the member's question and today's date, then the skill's facts.
    `not_in_this_data` tells the model what to do when the facts do not answer the question."""
    return {
        "current_question": current_question(context),
        "today": today_iso(),
        **values,
        "not_in_this_data": (
            "When these facts do not answer the question, say that you do not have that detail, "
            "and say where these facts tell the member to look."
        ),
    }
