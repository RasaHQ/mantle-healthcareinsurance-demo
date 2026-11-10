"""Tools of the out_of_pocket skill.

`my_costs` takes no arguments: the member and the plan come from the session only, so nothing the
member types selects whose spending is read.
"""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.authored_facts import facts_payload
from lib.member_data import PLANS, out_of_pocket, plan_id


@tool(
    description=(
        "The member's premium, how it is paid, the maximum out-of-pocket limit, the amount spent this year "
        "and the amount left before the limit and before the yearly drug cap. Takes no arguments."
    )
)
async def my_costs(context: ToolContext = None) -> ToolResult:
    costs = out_of_pocket(context)
    if costs is not None:
        return ToolResult(llm_response=facts_payload(context, signed_in=True, **costs))
    plan = plan_id(context)
    plans = [PLANS["plans"][plan]] if plan else list(PLANS["plans"].values())
    limits = {p["name"]: {"monthly_premium": p["monthly_premium"], "max_out_of_pocket": p["max_out_of_pocket"]} for p in plans}
    return ToolResult(
        llm_response=facts_payload(
            context,
            signed_in=False,
            plan_limits=limits,
            part_d_out_of_pocket_cap=PLANS["program"]["part_d_out_of_pocket_cap"],
            part_b_premium=PLANS["program"]["part_b_premium"],
            spending="Not available: the person is not signed in. They can log in at example.com/member to see it.",
        )
    )
