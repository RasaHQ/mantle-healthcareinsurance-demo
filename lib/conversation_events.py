"""Facts about the conversation, read from the tracker events that a tool receives."""

from __future__ import annotations

from typing import Any

DECLINE_SKILL_ID = "builtin_unsupported_request_handler"

# Skills that are not a topic of the member's: the engine's skills, the opener, the conversation
# patterns, the close and the handoff itself.
NON_TOPIC_SKILLS = frozenset({
    "builtin_session_start", "builtin_completed", "builtin_continue_interrupted",
    "builtin_unsupported_request_handler", "builtin_customer_satisfaction", "initialize_conversation",
    "greeting", "is_this_a_bot", "abusive_language", "thanks_reply", "farewell", "resolution_question",
    "representative_request", "representative_topic", "member_services_handoff", "language_assistance", "medical_advice",
})


def _event_type(event: Any) -> str:
    return type(event).__name__


def decline_streak(context: Any) -> int:
    """How many of the member's newest turns, in a row, ended in the decline. A turn that started
    a topic skill ends the count. A turn that started no skill (a follow-up) is skipped."""
    count = 0
    started: set[str | None] = set()
    for event in reversed(context.events):
        if _event_type(event) == "SkillActivated":
            started.add(getattr(event, "skill_id", None))
            continue
        if _event_type(event) != "UserUttered":
            continue
        if DECLINE_SKILL_ID in started:
            count += 1
        elif started - NON_TOPIC_SKILLS:
            break
        started = set()
    return count


def last_topic(context: Any) -> str | None:
    """The newest topic skill of this conversation, or None when the member named no topic yet."""
    for event in reversed(context.events):
        if _event_type(event) != "SkillActivated":
            continue
        skill = getattr(event, "skill_id", None)
        if skill and skill not in NON_TOPIC_SKILLS:
            return skill
    return None
