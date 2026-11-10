"""Tools of the find_provider skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import current_question
from lib.member_data import PLANS, SPECIALTIES, find_providers, member_record, plan_id, provider_entry


@tool(
    description=(
        "Finds providers by specialty, ZIP code or name, with their network status for the member's plan, "
        f"and the member's own PCP. Specialties: {', '.join(SPECIALTIES)}."
    )
)
async def find_doctor(specialty: str = "", zip_code: str = "", name: str = "", context: ToolContext = None) -> ToolResult:
    """Find providers.

    Args:
        specialty: The specialty, from the list in the description, for example "cardiology". Empty when the member names none.
        zip_code: The 5-digit ZIP code that the member gave. Empty when the member gave none.
        name: The provider's name as the member says it, for example "Dr. Patel". Empty when the member names none.
    """
    plan = plan_id(context)
    result: dict = {"current_question": current_question(context)}
    if specialty or zip_code or name:
        result.update(find_providers(specialty, zip_code, name, plan))
    record = member_record(context)
    if record:
        result["your_pcp"] = provider_entry(record["pcp"])
    if plan == "hmo":
        result["referral_rule"] = "On the HMO, you need a referral from your PCP to see a specialist."
    result["network"] = PLANS["plans"][plan]["network"] if plan else "The network depends on the plan."
    result["directory"] = "The full provider directory is at example.com/find-a-doctor."
    return ToolResult(llm_response=result)
