"""Tools of the decline skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.conversation_events import decline_streak


@tool(
    description=(
        "Block step of the decline: how many of the member's turns in a row ended in the decline. "
        "Takes no arguments."
    )
)
async def tally_declines(context: ToolContext = None) -> ToolResult:
    context.memory.set("decline_streak", decline_streak(context))
    return ToolResult()
