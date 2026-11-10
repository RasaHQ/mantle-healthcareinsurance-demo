---
name: Farewell
description: The member says goodbye or says that they are done, without asking anything new.
---

:::ordered_block id=sequence
steps:
  # The conversation already ended in this turn (a transfer, or the end of the chat).
  - id: already_over

    noop: true
    next:
      - if: "session.project.chat_ended or session.project.handoff_to_agent"
        then: END

      - else: relock

  - id: relock

    set_memory:
      closed_by_member: true
    next: resolve

  # After a no, resolution_question offers a person, and the close ends there.
  - id: resolve

    call: resolution_question
    next:
      - if: "session.resolution_question.resolution_result != 'not_answered'"
        then: send_farewell

      - else: END

  - id: send_farewell

    action: utter_goodbye
    next: go_satisfaction

  - id: go_satisfaction

    link: builtin_customer_satisfaction
:::
