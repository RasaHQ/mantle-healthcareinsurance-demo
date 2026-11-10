"""Tools of the resolution_question skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.question_gate import keep_reply


@tool(description="Runs after answered is set: keeps only the member's answer to the resolution question.")
async def run_after_setting_resolved_reply(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, "resolution_question", "resolved_reply")
