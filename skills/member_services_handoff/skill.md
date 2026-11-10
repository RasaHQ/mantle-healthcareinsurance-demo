---
name: Member Services Handoff
description: >
  The offer of a person - checks whether an agent is available, asks for the member's consent,
  asks for a name when the member is not signed in, and transfers the chat. Started by
  representative_request and by every skill that offers a person; never by routing.
hidden: true

# Block-only tools. The transfer also requires the member's yes, an available agent and a name, so
# it cannot run from any other path, also not from the block when one of these is missing.
tool_constraints:
  - check_member_services_hours:
      requires: "session.member_services_handoff.tool_gate_open"
  - hand_to_representative:
      requires: >-
        session.member_services_handoff.tool_gate_open
        and not session.project.handoff_to_agent
        and session.member_services_handoff.consent_given
        and session.member_services_handoff.hours_status == 'available'
        and (session.project.first_name_on_file or session.member_services_handoff.caller_name)
      on_success: utter_connecting_to_representative
---

:::ordered_block id=sequence
steps:
  - id: unlock_verify

    set_memory:
      handoff_started: true
      tool_gate_open: true
    next: inspect

  - id: inspect

    execute_tool: check_member_services_hours
    next: relock_verify

  - id: relock_verify

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.member_services_handoff.hours_status == 'available'"
        then: begin_propose

      - else: send_closed_hours

  # The consent question: a closed question that starts a transfer. The gate rolls back an answer
  # that the member did not give to this question. One retry; a second unclear answer is a no.
  - id: begin_propose

    set_memory:
      reasked: null
    next: unlock_propose

  - id: unlock_propose

    set_memory:
      consent_reply: null
      consent_given: null
      consent_reply_question_open: true
    next: prompt_propose

  - id: prompt_propose

    collect: consent_reply
    ask_before_filling: true
    utterance: utter_ask_consent_to_transfer
    next:
      - if: "session.member_services_handoff.consent_reply == 'yes'"
        then: require_caller

      - if: "session.member_services_handoff.consent_reply == 'no' or session.member_services_handoff.reasked"
        then: send_refused

      - else: reprompt_propose

  - id: reprompt_propose

    set_memory:
      reasked: true
    next: unlock_propose

  - id: require_caller

    noop: true
    next:
      - if: "not session.project.first_name_on_file"
        then: unlock_caller

      - else: unlock_pass_on

  - id: unlock_caller

    set_memory:
      caller_name: null
      caller_name_question_open: true
    next: prompt_caller

  - id: prompt_caller

    collect: caller_name
    ask_before_filling: true
    utterance: utter_ask_caller_name
    next: unlock_pass_on

  - id: unlock_pass_on

    set_memory:
      tool_gate_open: true
    next: run_pass_on

  - id: run_pass_on

    execute_tool: hand_to_representative
    next: relock_pass_on

  - id: relock_pass_on

    set_memory:
      tool_gate_open: false
    next: await_member

  - id: send_refused

    action: utter_what_else
    next: await_member

  - id: send_closed_hours

    action: utter_member_services_closed
    next: await_member

  # Every path ends the turn: no wrap-up question follows the offer.
  - id: await_member

    action: action_listen
    next: END

:::
