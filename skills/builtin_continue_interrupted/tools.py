"""Tools of the builtin_continue_interrupted skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

# The display name of initialize_conversation. The engine seeds `interrupted_task_name` with the
# paused skill's name and its description, and a block condition has no prefix match.
OPENER_NAME = "Initialize Conversation"


@tool(
    description=(
        "Block step of the resume skill: answers the resume question with no when the interrupted "
        "task is the opener and the member is qualified. Takes no arguments."
    )
)
async def drop_finished_opener(context: ToolContext = None) -> ToolResult:
    name = context.memory.get("interrupted_task_name") or ""
    qualified = context.memory.get("project.membership") and context.memory.get("project.plan_type")
    if name.startswith(OPENER_NAME) and qualified:
        context.memory.set("wants_to_resume", False)
    return ToolResult()
