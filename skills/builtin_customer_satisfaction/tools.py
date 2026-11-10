"""Tools of the satisfaction skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.question_gate import keep_reply


@tool(description="Block step of the satisfaction skill: ends the chat. Takes no arguments.")
async def close_chat(context: ToolContext = None) -> ToolResult:
    if not context.memory.get("project.chat_ended"):
        context.memory.set("project.chat_ended", True)
    return ToolResult()


@tool(description="Runs after csat_score is set: keeps only the member's answer to the rating question.")
async def run_after_setting_csat_score(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, "builtin_customer_satisfaction", "csat_score")
