---
name: Is This a Bot
description: The member asks whether they talk to a bot, an AI or a real person.
---

:::ordered_block id=sequence
steps:
  - id: send_robot

    action: utter_iamabot
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
