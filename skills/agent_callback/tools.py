"""Tools of the agent_callback skill."""

from __future__ import annotations

import re

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.question_gate import keep_reply

SKILL_ID = "agent_callback"
# 7 to 15 digits, with an optional leading +. Spaces, dashes, dots and brackets are removed first.
_PHONE = re.compile(r"^\+?\d{7,15}$")


@tool(description="Block step of the callback: books the call. Takes no arguments.")
async def book_callback(context: ToolContext = None) -> ToolResult:
    context.memory.set("callback_booked", True)
    return ToolResult(llm_response={"booked": True})


@tool(description="Runs after wants_callback is set: keeps only the member's answer to the callback question.")
async def run_after_setting_wants_callback(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, SKILL_ID, "wants_callback")


@tool(description="Runs after phone_number is set: keeps only a valid number given in answer to the question.")
async def run_after_setting_phone_number(context: ToolContext = None) -> ToolResult:
    raw = str(context.memory.get("phone_number") or "")
    number = re.sub(r"[\s\-().]", "", raw)
    if not _PHONE.match(number):
        # Reject before the gate: the question stays open, and the step asks again.
        return ToolResult(
            llm_response={
                "error": f"'{raw}' is not a valid phone number. Ask the member for a phone number with 7 to 15 digits."
            }
        )
    return keep_reply(context, SKILL_ID, "phone_number")
