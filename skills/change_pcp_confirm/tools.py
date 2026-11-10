"""Tools of the change_pcp_confirm skill.

The demo has no back end: submit_pcp_change makes a reference and writes it to memory. A real
assistant calls the enrollment system here, with the reference as an idempotency key.
"""

from __future__ import annotations

import uuid
from datetime import date

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import today_iso, us_date
from lib.question_gate import keep_reply
from lib.member_data import PROVIDERS, member_record

SKILL_ID = "change_pcp_confirm"


def _first_of_next_month(day: date) -> date:
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


@tool(description="Block step of the PCP change: reads the current and the new PCP, and the effective date. Takes no arguments.")
async def prepare_pcp_change(context: ToolContext = None) -> ToolResult:
    record = member_record(context)
    new_id = context.memory.get("change_pcp.new_pcp_id")
    if record is None or new_id not in PROVIDERS:
        context.memory.set("new_pcp_name", None)
        return ToolResult()
    context.memory.set("current_pcp_name", PROVIDERS[record["pcp"]]["name"])
    context.memory.set("new_pcp_name", PROVIDERS[new_id]["name"])
    context.memory.set("effective_date", us_date(_first_of_next_month(date.fromisoformat(today_iso()))))
    return ToolResult()


@tool(
    description=(
        "Block step of the PCP change: changes the member's PCP, after both of the member's yes answers. "
        "Takes no arguments."
    )
)
async def submit_pcp_change(context: ToolContext = None) -> ToolResult:
    # The tool constraint already requires both answers. The check here is a second line, in case
    # the constraint is ever changed.
    if context.memory.get("proceed_reply") != "yes" or context.memory.get("confirm_reply") != "yes":
        return ToolResult(llm_response={"error": "change refused: the member did not confirm twice"})
    if member_record(context) is None:
        return ToolResult(llm_response={"error": "change refused: nobody is signed in"})
    if context.is_cancelled:
        return ToolResult(llm_response={"error": "interrupted"})
    reference = "PCP-" + uuid.uuid4().hex[:8].upper()
    context.memory.set("change_reference", reference)
    return ToolResult(llm_response={"changed": True, "reference": reference})


@tool(description="Runs after proceed_reply is set: keeps only the member's answer to the continue question.")
async def run_after_setting_proceed_reply(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, SKILL_ID, "proceed_reply")


@tool(description="Runs after confirm_reply is set: keeps only the member's answer to the confirm question.")
async def run_after_setting_confirm_reply(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, SKILL_ID, "confirm_reply")
