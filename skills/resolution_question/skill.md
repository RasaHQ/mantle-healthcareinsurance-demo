---
name: Resolution Question
description: >
  The resolution question when the member is done - "Did I answer your question today?" - and
  the offer of a person after a no. The thanks_reply and farewell skills call it.
hidden: true
---

:::ordered_block id=sequence
steps:
  # A closed question: the answer field has `unclear`, one retry, and a fallback. The gate rolls
  # back an answer written before the question was asked. After a second unclear answer, the
  # close goes on without the offer of a person.
  - id: begin

    set_memory:
      reasked: null
      resolution_result: null
    next: unlock_prompt

  - id: unlock_prompt

    set_memory:
      resolved_reply: null
      resolved_reply_question_open: true
    next: prompt

  - id: prompt

    collect: resolved_reply
    ask_before_filling: true
    utterance: utter_ask_question_answered
    next:
      - if: "session.resolution_question.resolved_reply == 'yes'"
        then: replied_affirmed

      - if: "session.resolution_question.resolved_reply == 'no'"
        then: replied_denied

      - if: "session.resolution_question.reasked"
        then: replied_vague

      - else: reprompt_prompt

  - id: reprompt_prompt

    set_memory:
      reasked: true
    next: unlock_prompt

  - id: replied_affirmed

    set_memory:
      resolution_result: answered
    next: END

  - id: replied_vague

    set_memory:
      resolution_result: unclear
    next: END

  - id: replied_denied

    set_memory:
      resolution_result: not_answered
    next: propose_rep

  - id: propose_rep

    call: member_services_handoff
    next: END

:::
