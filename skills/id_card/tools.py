"""Tools of the id_card skill.

The address comes from the member record of the session's member, never from the chat. The demo
has no back end: order_card makes a reference and writes it to memory.
"""

from __future__ import annotations

import uuid

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.question_gate import keep_reply
from lib.member_data import member_record


@tool(description="Block step of the ID card skill: reads the mailing address on file. Takes no arguments.")
async def load_address(context: ToolContext = None) -> ToolResult:
    record = member_record(context)
    context.memory.set("mailing_address", record["mailing_address"] if record else None)
    return ToolResult()


@tool(description="Block step of the ID card skill: orders a new card, after the member's yes. Takes no arguments.")
async def order_card(context: ToolContext = None) -> ToolResult:
    if context.memory.get("address_reply") != "yes" or member_record(context) is None:
        return ToolResult(llm_response={"error": "order refused: the address was not confirmed"})
    reference = "CARD-" + uuid.uuid4().hex[:8].upper()
    context.memory.set("order_reference", reference)
    return ToolResult(llm_response={"ordered": True, "reference": reference})


@tool(description="Runs after address_reply is set: keeps only the member's answer to the address question.")
async def run_after_setting_address_reply(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, "id_card", "address_reply")
