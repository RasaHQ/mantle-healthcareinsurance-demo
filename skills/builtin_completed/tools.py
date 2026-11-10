"""Tools of the builtin_completed skill (the wrap-up)."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

# Events after the member's message that show that a skill handled it.
HANDLING_EVENTS = ("BotUttered", "SkillCompleted", "OrderedBlockCompleted")

# Engine skills that complete at the member's next message without handling it.
PASSIVE_SKILLS = frozenset({"builtin_continue_interrupted", "builtin_session_start"})


@tool(
    description=(
        "Block step of the wrap-up: whether the member sent a message after the wrap-up started "
        "that nothing handled yet. Takes no arguments."
    )
)
async def detect_unhandled_message(context: ToolContext = None) -> ToolResult:
    unhandled_message = False
    started_after_message = False
    for event in reversed(context.events):
        kind = type(event).__name__
        if not unhandled_message and kind in HANDLING_EVENTS and getattr(event, "skill_id", None) not in PASSIVE_SKILLS:
            break
        if kind == "UserUttered":
            unhandled_message = True
            if started_after_message:
                break
        if kind == "SkillActivated" and getattr(event, "skill_id", None) == "builtin_completed":
            if unhandled_message:
                break
            started_after_message = True
    context.memory.set("unhandled_message", unhandled_message)
    return ToolResult()


@tool(description="Block step of the wrap-up: clears the request that the precondition parked. Takes no arguments.")
async def forget_pending_request(context: ToolContext = None) -> ToolResult:
    context.memory.set("project.pending_request", None)
    return ToolResult()
