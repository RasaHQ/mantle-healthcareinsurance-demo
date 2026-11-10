"""The question gate: an answer counts only when the member gave it after the question was asked.

Use it for a closed question whose answer starts an action (a transfer, a cancellation, a rating).

1. Right before the `collect:` step, a `set_memory` step sets `<field>_ask_open: true`.
2. The answer field is `llm_settable`, so the model records the member's answer from typed words.
3. The skill's `run_after_setting_<field>` tool calls `keep_reply`. It keeps the write only when
   the member's latest message came after the gate opened, and no newer question opened its own
   gate since. Any other write is rolled back: the engine rolls back a write when the post-write
   tool returns an `error`.

Without the gate, the model can fill the answer from an earlier remark ("yes, and also ..."), or
in the same turn that asked the question, and the action starts without the member's answer.
"""

from __future__ import annotations

from typing import Any

from rasa.mantle.tools.result import ToolResult

GATE_SUFFIX = "_question_open"


def _opened_gate(event: Any) -> str | None:
    """The qualified gate name (`<skill>.<field>_ask_open`) when `event` opens a gate, else None."""
    if type(event).__name__ != "MemorySet":
        return None
    key = getattr(event, "key", None)
    if isinstance(key, str) and key.endswith(GATE_SUFFIX) and getattr(event, "value", None) is True:
        return key
    return None


def answered_after_opening(context: Any, gate: str) -> bool:
    """True when a member message follows the newest opening of `gate`, and no other gate opened
    after that message's question. `gate` is qualified: `<skill>.<field>_ask_open`."""
    member_spoke = False
    for event in reversed(context.events):
        if type(event).__name__ == "UserUttered":
            member_spoke = True
            continue
        opened = _opened_gate(event)
        if opened == gate:
            return member_spoke
        if opened is not None and member_spoke:
            # A newer question was asked: the member's message answers that one.
            return False
    return False


def keep_reply(context: Any, skill_id: str, field: str) -> ToolResult:
    """The body of `run_after_setting_<field>`: keep the answer, or roll the write back."""
    gate = f"{field}{GATE_SUFFIX}"
    if not context.memory.get(gate) or not answered_after_opening(context, f"{skill_id}.{gate}"):
        return ToolResult(
            llm_response={
                "error": (
                    f"{field} was not asked yet, so it was not recorded. Do not set it: "
                    f"the {skill_id} skill asks this question itself."
                )
            }
        )
    context.memory.set(gate, False)
    return ToolResult(llm_response={"recorded": {field: context.memory.get(field)}})
