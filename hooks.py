"""Project hooks.

One hook: on the first model call of a turn that follows the decline, it adds one paragraph to the
system prompt. After a decline, models tend to offer help that no skill gives ("I can check that
for you"). No tool result reaches that turn, so a prompt note is the only lever. It is prose: it
lowers the rate of such offers, it cannot stop them.
"""

from __future__ import annotations

from rasa.mantle.hooks import ModelRequestPayload, modify_model_request

# The first words of both decline responses in responses.yml.
DECLINE_START = "I'm not able to help with that one."

AFTER_DECLINE_NOTE = (
    "\n\n## This turn\n"
    "The previous reply was the decline. If a skill or a block covers the member's new message, "
    "start it. Otherwise, if an authored response already in this conversation answers it, repeat "
    "that answer in one sentence. Otherwise decline with cannot_help. Offer nothing further: no "
    "explanation, no check, no question back."
)


@modify_model_request()
async def note_after_decline(request: ModelRequestPayload) -> ModelRequestPayload:
    messages = request.messages
    if request.iteration != 0 or not messages or messages[-1].get("role") != "user":
        return request
    previous = next(
        (m for m in reversed(messages[:-1]) if m.get("role") == "assistant" and m.get("content")),
        None,
    )
    if previous is None or not str(previous.get("content", "")).startswith(DECLINE_START):
        return request
    edited = [dict(m) for m in messages]
    if edited[0].get("role") == "system":
        edited[0]["content"] = (edited[0].get("content") or "") + AFTER_DECLINE_NOTE
    return request.model_copy(update={"messages": edited})
