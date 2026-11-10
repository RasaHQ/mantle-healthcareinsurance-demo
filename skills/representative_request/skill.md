---
name: Representative Request
description: >
  A person - the member asks to talk to a person, a human, a representative, an agent or Member Services. Asking
  who can help with something the assistant declined is asking for one. A question that the
  assistant cannot answer is declined with cannot_help, never with this skill.
precondition: membership_known

# Block-only tool: the gate is open only while the block runs it.
tool_constraints:
  - choose_representative_path:
      requires: "session.representative_request.tool_gate_open"
---

:::ordered_block id=sequence
steps:
  # The member chose a person: the task that this request interrupted is dropped.
  - id: unlock_begin

    set_memory:
      tool_gate_open: true
      asked_for_representative: true
    next: begin

  - id: begin

    execute_tool: choose_representative_path
    next: relock_begin

  - id: relock_begin

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.representative_request.chosen_path == 'closed'"
        then: go_transfer

      - if: "session.representative_request.chosen_path == 'earlier_topic'"
        then: send_connect

      - else: prompt_subject

  # The member named a topic earlier: offer a person for it.
  - id: send_connect

    action: utter_representative_can_help
    next: go_transfer

  - id: go_transfer

    link: member_services_handoff

  # No topic yet: ask what it is about. The topic's skill may answer it without a person.
  - id: prompt_subject

    link: representative_topic
:::
