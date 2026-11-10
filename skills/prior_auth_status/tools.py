"""Tools of the prior_auth_status skill.

`load_authorizations` reads the requests of the session's member into skill memory.
`authorizations_on_record` gives them to the model with the authored rules and next steps. Neither
tool takes an argument, so nothing the member types selects whose requests are read.
"""

from __future__ import annotations

from pathlib import Path

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import AuthoredTexts, facts_payload, us_date
from lib.member_data import authorizations

TEXTS = AuthoredTexts(Path(__file__).parent)
DATE_FIELDS = ("submitted", "decided", "valid_until", "decision_due_by")


@tool(description="Block step of prior_auth_status: loads the signed-in member's requests. Takes no arguments.")
async def load_authorizations(context: ToolContext = None) -> ToolResult:
    found = authorizations(context)
    if found is None:
        context.memory.set("loaded", False)
        return ToolResult()
    readable = [{k: (us_date(v) if k in DATE_FIELDS and v else v) for k, v in item.items()} for item in found]
    context.memory.set("authorizations", readable)
    context.memory.set("loaded", True)
    return ToolResult()


@tool(
    description=(
        "The signed-in member's prior authorizations and drug coverage requests, newest first: service, "
        "status, dates, the reason of a denial, the decision rules and the next step of each status. "
        "Takes no arguments."
    )
)
async def authorizations_on_record(context: ToolContext = None) -> ToolResult:
    records = context.memory.get("authorizations") or []
    statuses = sorted({r["status"] for r in records})
    types = sorted({r["type"] for r in records})
    return ToolResult(
        llm_response=facts_payload(
            context,
            requests=records,
            number_of_requests=len(records),
            decision_rules={t: TEXTS.variant_text(f"utter_auth_rules_{t}", context) for t in types},
            next_step_by_status={s: TEXTS.variant_text(f"utter_auth_next_step_{s}", context) for s in statuses},
        )
    )
