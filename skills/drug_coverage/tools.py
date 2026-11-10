"""Tools of the drug_coverage skill.

The drug name and strength are the member's own words, so the model passes them. The plan comes
from the session, never from an argument.
"""

from __future__ import annotations

from datetime import date, timedelta

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import current_question, today_iso
from lib.member_data import FORMULARY, PLANS, check_drug as lookup_drug, member_record, plan_id

NEW_MEMBER_DAYS = 90


def _new_member_note(context: ToolContext) -> dict:
    """The transition fill rule, for a member in their first 90 days in the plan."""
    record = member_record(context)
    if not record:
        return {}
    since = date.fromisoformat(today_iso()) - date.fromisoformat(record["effective_date"])
    if timedelta(0) <= since < timedelta(days=NEW_MEMBER_DAYS):
        return {"new_member_transition": FORMULARY["new_member_transition"]}
    return {}


@tool(
    description=(
        "Looks up a drug on the plan's drug list: tier, cost at preferred and standard pharmacies and by "
        "mail order, prior authorization, step therapy and quantity limits."
    )
)
async def check_drug(drug_name: str, strength: str = "", context: ToolContext = None) -> ToolResult:
    """Look up one drug.

    Args:
        drug_name: The drug's brand or generic name, as the member says it, for example "Eliquis" or "metformin".
        strength: The strength, when the member gives it, for example "5 mg". Empty otherwise.
    """
    result = {"current_question": current_question(context)}
    result.update(lookup_drug(drug_name, strength, plan_id(context)))
    if result.get("on_drug_list"):
        result.update(_new_member_note(context))
    return ToolResult(llm_response=result)


@tool(
    description=(
        "Facts about pharmacies, mail order, the yearly cap on drug costs, insulin costs and the Medicare "
        "Prescription Payment Plan. Takes no arguments."
    )
)
async def pharmacy_facts(context: ToolContext = None) -> ToolResult:
    plan = plan_id(context)
    deductible = PLANS["plans"][plan]["pharmacy"]["deductible"] if plan else {
        p["name"]: p["pharmacy"]["deductible"] for p in PLANS["plans"].values()
    }
    return ToolResult(
        llm_response={
            "current_question": current_question(context),
            "pharmacy_network": FORMULARY["pharmacy_network"],
            "mail_order": FORMULARY["mail_order"],
            "drug_deductible": deductible,
            "part_d_out_of_pocket_cap": PLANS["program"]["part_d_out_of_pocket_cap"],
            "insulin": PLANS["program"]["insulin"],
            "prescription_payment_plan": PLANS["program"]["prescription_payment_plan"],
        }
    )
