---
name: Agent Callback
description: >
  A call from a licensed agent about the plan options during an enrollment period - offered to a
  member who wants to switch plans. Asks whether the member wants the call, then the phone number,
  then books it. Called by enrollment_changes only.
hidden: true

# Block-only tool. The booking also requires the member's yes and a valid phone number.
tool_constraints:
  - book_callback:
      requires: >-
        session.agent_callback.tool_gate_open
        and session.agent_callback.wants_callback == 'yes'
        and session.agent_callback.phone_number
---

:::ordered_block id=sequence
steps:
  - id: unlock_propose

    set_memory:
      wants_callback: null
      wants_callback_question_open: true
    next: prompt_propose

  - id: prompt_propose

    collect: wants_callback
    ask_before_filling: true
    utterance: utter_ask_wants_callback
    next:
      - if: "session.agent_callback.wants_callback == 'yes'"
        then: unlock_phone_no

      - else: send_denied_call

  - id: send_denied_call

    action: utter_what_else
    next: END

  # A free-text question. The post-write tool checks the number, and rejects it with a reason;
  # the step then asks again.
  - id: unlock_phone_no

    set_memory:
      phone_number: null
      phone_number_question_open: true
    next: prompt_phone_no

  - id: prompt_phone_no

    collect: phone_number
    ask_before_filling: true
    utterance: utter_ask_phone_number
    next: unlock_book

  - id: unlock_book

    set_memory:
      tool_gate_open: true
    next: book

  - id: book

    execute_tool: book_callback
    next: relock_book

  - id: relock_book

    set_memory:
      tool_gate_open: false
    next: send_booked

  - id: send_booked

    action: utter_callback_booked
    next: END

:::
