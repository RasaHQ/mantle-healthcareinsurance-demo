"""Tools of the representative_request skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib import service_hours
from lib.conversation_events import last_topic


@tool(
    description=(
        "Block step of representative_request: whether an agent is available, and whether the member named "
        "a topic earlier. Takes no arguments."
    )
)
async def choose_representative_path(context: ToolContext = None) -> ToolResult:
    if not service_hours.member_services_open(context):
        route = "closed"
    elif last_topic(context):
        route = "earlier_topic"
    else:
        route = "ask"
    context.memory.set("chosen_path", route)
    return ToolResult()
