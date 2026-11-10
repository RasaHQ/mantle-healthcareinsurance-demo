---
name: Abusive Language
description: The member insults the assistant or uses abusive language, without a question.
---

:::ordered_block id=sequence
steps:
  - id: send_calm

    action: utter_abuse_reply
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
