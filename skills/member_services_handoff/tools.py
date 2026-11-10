"""Tools of the member_services_handoff skill."""

from __future__ import annotations

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

from lib import service_hours
from lib.question_gate import answered_after_opening, keep_reply


def _check(context: ToolContext) -> str:
    status = "available" if service_hours.member_services_open(context) else "unavailable"
    context.memory.set("hours_status", status)
    context.memory.set("hours_text", service_hours.hours_text())
    return status


@tool(description="Block step of the handoff: whether a human agent can take the chat now. Takes no arguments.")
async def check_member_services_hours(context: ToolContext = None) -> ToolResult:
    return ToolResult(llm_response={"status": _check(context)})


@tool(
    description=(
        "Block step of the handoff: hands the chat to a human agent after the member said yes. "
        "Takes no arguments."
    )
)
async def hand_to_representative(context: ToolContext = None) -> ToolResult:
    # The hours may have changed since the check at the start of the block.
    if _check(context) != "available":
        return ToolResult(llm_response={"error": "transfer refused: no agent is available now", "transferred": False})
    name = context.memory.get("project.first_name_on_file") or context.memory.get("caller_name")
    if not context.memory.get("project.handoff_to_agent"):
        context.memory.set("project.handoff_to_agent", True)
    return ToolResult(llm_response={"transferred": True, "name_given_to_agent": name})


@tool(description="Runs after consent_reply is set: keeps only the member's answer to the consent question.")
async def run_after_setting_consent_reply(context: ToolContext = None) -> ToolResult:
    if not context.memory.get("consent_reply_question_open") or not answered_after_opening(
        context, "member_services_handoff.consent_reply_question_open"
    ):
        return ToolResult(
            llm_response={
                "error": (
                    "consent_reply was not answered yet, so it was not recorded. The member_services_handoff "
                    "skill asks the member itself."
                )
            }
        )
    context.memory.set("consent_reply_question_open", False)
    context.memory.set("consent_given", context.memory.get("consent_reply") == "yes")
    return ToolResult(llm_response={"recorded": {"consent_given": context.memory.get("consent_given")}})


@tool(description="Runs after caller_name is set: keeps only a name given in answer to the name question.")
async def run_after_setting_caller_name(context: ToolContext = None) -> ToolResult:
    return keep_reply(context, "member_services_handoff", "caller_name")
