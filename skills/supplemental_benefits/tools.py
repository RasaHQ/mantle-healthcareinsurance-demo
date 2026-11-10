"""Tools of the supplemental_benefits skill: the block notes the authored texts for the member's
plan, and the model answers from extra_benefit_facts. A signed-in member also gets the OTC balance."""

from __future__ import annotations

from pathlib import Path

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import AuthoredTexts, facts_payload, note_authored, authored_notes
from lib.member_data import member_record

TEXTS = AuthoredTexts(Path(__file__).parent)


@tool(description="Block step only: notes the authored text of one extra benefit for this member. Takes the response name.")
async def note_benefit_text(response: str, context: ToolContext = None) -> ToolResult:
    note_authored(context, TEXTS, response)
    return ToolResult()


@tool(
    description=(
        "The authored texts of the extra benefits (dental, vision, hearing, OTC, fitness, rides, meals) "
        "for this member's plan, and the OTC balance of a signed-in member. Takes no arguments."
    )
)
async def extra_benefit_facts(context: ToolContext = None) -> ToolResult:
    record = member_record(context)
    extra = {}
    if record:
        extra["otc_balance_this_quarter"] = record["otc_balance_this_quarter"]
    else:
        extra["otc_balance_this_quarter"] = "Not available: the person is not signed in."
    return ToolResult(llm_response=facts_payload(context, authored_texts=authored_notes(context), **extra))
