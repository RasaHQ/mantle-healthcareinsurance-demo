"""Tools of the claim_status skill.

`load_claims` reads the claims of the session's member into skill memory. `my_claims` gives
them to the model with the authored next step of each status. Neither tool takes an argument, so
nothing the member types selects whose claims are read.
"""

from __future__ import annotations

from pathlib import Path

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import AuthoredTexts, facts_payload
from lib.member_data import member_claims, member_record

TEXTS = AuthoredTexts(Path(__file__).parent)


@tool(description="Block step of claim_status: loads the signed-in member's claims. Takes no arguments.")
async def load_claims(context: ToolContext = None) -> ToolResult:
    found = member_claims(context)
    if found is None:
        context.memory.set("claims_loaded", False)
        return ToolResult()
    context.memory.set("claim_records", found)
    context.memory.set("claims_loaded", True)
    return ToolResult()


@tool(
    description=(
        "The signed-in member's claims, newest first: service date, provider, service, status, the amount "
        "billed, what the plan paid and what the member owes, the reason of a denied claim, and the next "
        "step of each status. Takes no arguments."
    )
)
async def my_claims(context: ToolContext = None) -> ToolResult:
    records = context.memory.get("claim_records") or []
    next_steps = {
        status: TEXTS.variant_text(f"utter_claim_next_step_{status}", context)
        for status in sorted({claim["status"] for claim in records})
    }
    record = member_record(context)
    return ToolResult(
        llm_response=facts_payload(
            context,
            claims_of=f"{record['first_name']}, the signed-in member" if record else None,
            other_people="Claims of anyone else are not available in this chat.",
            member_claims=records,
            number_of_claims=len(records),
            next_step_by_status=next_steps,
        )
    )
