"""Tools of the benefit_check skill.

The procedure codes and service categories are the member's own words, so the model passes them.
The plan comes from the session, never from an argument.
"""

from __future__ import annotations

import re

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import current_question
from lib.member_data import CATEGORY_IDS, PLANS, check_services, plan_id

NEXT_STEP = (
    "These are the plan's coverage rules. When a service needs prior authorization, your provider asks "
    "us before the service, and our clinical team decides based on your situation. When a service needs "
    "a referral, ask your primary care provider (PCP) for one."
)


def _split(value: str | None) -> list[str]:
    """`"99213, 70551 and 99999"` -> `["99213", "70551", "99999"]`."""
    parts = re.split(r",|;|\band\b|\s+", value or "")
    return [part.strip() for part in parts if part.strip()]


@tool(
    description=(
        "Looks up what medical services cost on this member's plan, and whether they need prior "
        "authorization or a referral. When the plan is not known, it gives the cost on each plan. "
        f"Categories: {', '.join(CATEGORY_IDS)}."
    )
)
async def check_benefit(service_codes: str = "", categories: str = "", context: ToolContext = None) -> ToolResult:
    """Look up medical services.

    Args:
        service_codes: The procedure codes that the member gave, exactly as given, comma-separated, for example "99213, 70551".
        categories: The categories of the services that the member named, comma-separated, from the list in the description, for example "specialist, mri_ct".
    """
    codes = _split(service_codes)
    named = _split(categories)
    plan = plan_id(context)
    result: dict = {"current_question": current_question(context)}
    result.update(check_services(codes, named, plan))
    result["network"] = PLANS["plans"][plan]["network"] if plan else {p["name"]: p["network"] for p in PLANS["plans"].values()}
    result["out_of_network"] = (
        PLANS["plans"][plan]["out_of_network"] if plan else {p["name"]: p["out_of_network"] for p in PLANS["plans"].values()}
    )
    result["emergency"] = PLANS["program"]["emergency"]
    result["next_step"] = NEXT_STEP
    if not codes and not named:
        result["error"] = "No procedure code and no category given. Ask which service the member means."
    return ToolResult(llm_response=result)
