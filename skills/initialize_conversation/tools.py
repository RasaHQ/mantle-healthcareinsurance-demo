"""Tools of the initialize_conversation skill.

The member's facts come from the member record of the session's member id, never from the
conversation. For a visitor, the model records the answers to the opener's questions (from a
button tap or from typed words), and `store_opener_replies` copies them to project memory.
"""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.member_data import member_record

# The opener's answer field -> the project field it fills.
OPENER_TO_PROJECT = {
    "membership_reply": "project.membership",
    "plan_reply": "project.plan_type",
}
# The same answer fields, as qualified keys in MemorySet events.
REPLY_KEYS = tuple(f"initialize_conversation.{field}" for field in OPENER_TO_PROJECT)


def _set_once(context: ToolContext, key: str, value: object) -> None:
    """Project fields are write-once: write only a value that is set, into an unset field."""
    if value is not None and context.memory.get(key) is None:
        context.memory.set(key, value)


@tool(
    description=(
        "Block step of initialize_conversation: loads the signed-in member's name and plan into "
        "memory. Takes no arguments."
    )
)
async def load_member_record(context: ToolContext = None) -> ToolResult:
    record = member_record(context)
    if record is not None:
        _set_once(context, "project.first_name_on_file", record["first_name"])
        _set_once(context, "project.membership", "member")
        _set_once(context, "project.plan_type", record["plan"])
    _set_once(context, "project.opener_done", True)
    return ToolResult()


@tool(
    description=(
        "Block step of initialize_conversation: saves the member's latest message, the request that "
        "the precondition parked. Takes no arguments."
    )
)
async def remember_pending_request(context: ToolContext = None) -> ToolResult:
    request = next(
        (event.text for event in reversed(context.events) if type(event).__name__ == "UserUttered"),
        None,
    )
    context.memory.set("project.pending_request", request)
    return ToolResult()


def _question_typed_during_opener(context: ToolContext) -> str | None:
    """The newest member message in this opener run that answered none of its questions.

    A visitor can type a question while the opener asks its own question. The engine then parks the
    question's skill and asks again. That message is the request to answer after the opener."""
    events = list(context.events)
    start = max(
        (i for i, e in enumerate(events)
         if type(e).__name__ == "SkillActivated" and getattr(e, "skill_id", None) == "initialize_conversation"),
        default=0,
    )
    question, text, answered = None, None, False
    for event in events[start:]:
        kind = type(event).__name__
        if kind == "UserUttered":
            if text and not answered:
                question = text
            raw = (getattr(event, "text", "") or "").strip()
            text = None if raw.startswith(("/", "set:")) else raw
            answered = False
        elif (
            kind == "MemorySet"
            and getattr(event, "key", None) in REPLY_KEYS
            and getattr(event, "value", None) is not None
        ):
            answered = True
    if text and not answered:
        question = text
    return question


@tool(
    description=(
        "Block step of initialize_conversation: copies the visitor's answers to project memory. "
        "Takes no arguments."
    )
)
async def store_opener_replies(context: ToolContext = None) -> ToolResult:
    for answer_field, project_field in OPENER_TO_PROJECT.items():
        answer = context.memory.get(answer_field)
        if answer and answer != "unclear":
            _set_once(context, project_field, answer)
    if not context.memory.get("project.pending_request"):
        question = _question_typed_during_opener(context)
        if question:
            context.memory.set("project.pending_request", question)
    return ToolResult()
