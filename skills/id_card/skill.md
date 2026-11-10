---
name: ID Card
description: >
  The member ID card - a lost, damaged or missing card, a new card, when the card arrives, or the
  digital card in the app. For example "I lost my card", "Can you send me a new ID card?" or "Where
  do I find my digital card?". Also "Do I still need my red, white and blue Medicare card?".
precondition: membership_known

# Block-only tools. The order also requires the member's yes to the address question.
tool_constraints:
  - load_address:
      requires: "session.id_card.tool_gate_open"
  - order_card:
      requires: >-
        session.id_card.tool_gate_open
        and session.id_card.address_reply == 'yes'
        and not session.id_card.order_reference
---

:::ordered_block id=sequence
steps:
  - id: unlock_fetch

    set_memory:
      tool_gate_open: true
    next: fetch

  - id: fetch

    execute_tool: load_address
    next: relock_fetch

  - id: relock_fetch

    set_memory:
      tool_gate_open: false
      reasked: null
    next:
      - if: "session.id_card.mailing_address"
        then: send_digital

      - else: send_sign_in

  - id: send_sign_in

    action: utter_sign_in_for_member_data
    next: await_member

  - id: send_digital

    action: utter_id_card_digital
    next: unlock_addr

  # A closed question with a gate and one retry. Only a yes orders the card.
  - id: unlock_addr

    set_memory:
      address_reply: null
      address_reply_question_open: true
    next: prompt_addr

  - id: prompt_addr

    collect: address_reply
    ask_before_filling: true
    utterance: utter_ask_card_address
    next:
      - if: "session.id_card.address_reply == 'yes'"
        then: unlock_place

      - if: "session.id_card.address_reply == 'no'"
        then: send_change_addr

      - if: "session.id_card.reasked"
        then: send_not_ordered

      - else: reprompt_addr

  - id: reprompt_addr

    set_memory:
      reasked: true
    next: unlock_addr

  - id: unlock_place

    set_memory:
      tool_gate_open: true
    next: place

  - id: place

    execute_tool: order_card
    next: relock_place

  - id: relock_place

    set_memory:
      tool_gate_open: false
    next: send_ordered

  - id: send_ordered

    action: utter_card_ordered
    next: END

  # A wrong address is changed by a representative, who verifies the member's identity.
  - id: send_change_addr

    action: utter_card_change_address
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

  - id: send_not_ordered

    action: utter_card_not_ordered
    next: END

  - id: await_member

    action: action_listen
    next: END

:::
