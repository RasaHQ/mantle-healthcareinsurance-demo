---
name: Topic Wrap-up
description: "The wrap-up after a skill - asks whether the member needs more help, then the satisfaction question."
routing:
  engine_managed: true

# Block-only tools: the gate is open only while the block runs them.
tool_constraints:
  - detect_unhandled_message:
      requires: "session.builtin_completed.tool_gate_open"
  - forget_pending_request:
      requires: "session.builtin_completed.tool_gate_open"
---

:::ordered_block id=sequence
name: builtin_completed
steps:
  # No wrap-up after a transfer or after the end of the chat.
  - id: already_over

    noop: true
    next:
      - if: "session.project.handoff_to_agent or session.project.chat_ended"
        then: await_member

      - else: unlock_verify

  - id: await_member

    action: action_listen
    next: END

  # A block that ends with action_listen ends the turn before the wrap-up asks. The wrap-up then
  # starts at the member's next message, which is a new request: end here, and the model routes it.
  - id: unlock_verify

    set_memory:
      tool_gate_open: true
    next: inspect

  - id: inspect

    execute_tool: detect_unhandled_message
    next: wipe

  # The parked skill has run: its request leaves project memory.
  - id: wipe

    execute_tool: forget_pending_request
    next: relock_verify

  - id: relock_verify

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.builtin_completed.unhandled_message"
        then: END

      - else: prompt_proceed

  - id: prompt_proceed

    collect: wants_to_continue
    utterance: utter_ask_wants_to_continue
    description: >
      Does the member want help with something else? When they name a task, set this to true and
      start the skill of that task.
    next:
      - if: "session.builtin_completed.wants_to_continue"
        then: extra_help

      - else: go_satisfaction

  - id: extra_help

    instructions: >
      Ask what the member needs help with. When they name a task, start the skill of that task.
  - id: go_satisfaction

    link: builtin_customer_satisfaction
:::
