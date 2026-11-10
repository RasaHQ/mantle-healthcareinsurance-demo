---
name: Conversation Start
description: "Session start - runs initialize_conversation, which greets and qualifies the person."
routing:
  engine_managed: true
---

:::ordered_block id=sequence
name: builtin_session_start
steps:
  - id: qualify_caller

    call: initialize_conversation
    next: after_opener

  # Only after the visitor answered the plan question in this run. A signed-in member was asked
  # nothing, and the opener already ended the turn after the greeting.
  - id: after_opener

    noop: true
    next:
      - if: "session.initialize_conversation.plan_reply"
        then: send_offer_can_i_help

      - else: END

  - id: send_offer_can_i_help

    action: utter_offer_help
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
