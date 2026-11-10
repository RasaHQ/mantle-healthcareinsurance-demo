---
name: Decline
description: >
  The decline - sent when the member asks for something this assistant cannot help with.
  Started by the orchestrator's `cannot_help` tool, never by routing. This is the way to decline,
  never the member_services_handoff skill, which is only for a member who asks for a person.
routing:
  engine_managed: true

# Block-only tool: the gate is open only while the block runs it.
tool_constraints:
  - tally_declines:
      requires: "session.builtin_unsupported_request_handler.tool_gate_open"
---

:::ordered_block id=sequence
steps:
  # The third decline in a row gives the handover line and the offer of a person.
  - id: unlock_tally

    set_memory:
      tool_gate_open: true
    next: tally

  - id: tally

    execute_tool: tally_declines
    next: relock_tally

  - id: relock_tally

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.builtin_unsupported_request_handler.decline_streak >= 3"
        then: suggest_rep

      - else: by_request_type

  - id: suggest_rep

    action: utter_suggest_representative
    next: go_transfer

  - id: go_transfer

    link: member_services_handoff

  - id: by_request_type

    noop: true
    next:
      - if: "session.builtin_unsupported_request_handler.request_type == 'out_of_domain_out_of_scope'"
        then: decline_out_of_domain

      - else: decline_in_domain

  - id: decline_in_domain

    action: utter_decline_in_domain_out_of_scope
    next: await_member

  - id: decline_out_of_domain

    action: utter_decline_out_of_domain_out_of_scope
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
