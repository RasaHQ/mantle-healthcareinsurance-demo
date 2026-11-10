"""Tools of the change_pcp skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib.member_data import PROVIDERS, member_record, provider_entry

PCP_SPECIALTIES = ("family_medicine", "internal_medicine")


@tool(
    description=(
        "Checks whether a doctor can be the member's new primary care provider (PCP), and records the "
        "pick when the doctor can. The change itself needs the member's confirmation."
    )
)
async def pick_new_pcp(name: str, context: ToolContext = None) -> ToolResult:
    """Pick a new PCP.

    Args:
        name: The doctor's name as the member says it, for example "Dr. Kim".
    """
    record = member_record(context)
    if record is None:
        return ToolResult(llm_response={"error": "Nobody is signed in."})
    wanted = name.strip().lower().removeprefix("dr. ").removeprefix("dr ")
    matches = [pid for pid, p in PROVIDERS.items() if wanted and wanted in p["name"].lower()]
    if not matches:
        return ToolResult(llm_response={"can_be_pcp": False, "reason": f"No provider named '{name}' is in our directory."})
    candidates = [provider_entry(pid) for pid in matches]
    usable = [
        c for c in candidates
        if c["specialty"] in PCP_SPECIALTIES and record["plan"] in c["networks"] and c["accepting_new_patients"]
    ]
    if record["pcp"] in matches:
        return ToolResult(llm_response={"can_be_pcp": False, "reason": "This doctor is already the member's PCP."})
    if len(usable) == 1:
        context.memory.set("new_pcp_id", usable[0]["provider_id"])
        return ToolResult(llm_response={"can_be_pcp": True, "doctor": usable[0]})
    if len(usable) > 1:
        return ToolResult(llm_response={"can_be_pcp": False, "reason": "More than one doctor matches. Ask which one.", "matches": usable})
    reasons = []
    for c in candidates:
        why = []
        if c["specialty"] not in PCP_SPECIALTIES:
            why.append(f"is a {c['specialty'].replace('_', ' ')} specialist, not a primary care doctor")
        if record["plan"] not in c["networks"]:
            why.append("is not in network for the member's plan")
        if not c["accepting_new_patients"]:
            why.append("is not accepting new patients")
        reasons.append(f"{c['name']} " + " and ".join(why))
    return ToolResult(llm_response={"can_be_pcp": False, "reason": "; ".join(reasons)})
