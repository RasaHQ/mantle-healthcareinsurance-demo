---
name: Greeting
description: The member only says hello, without a question or a request.
---

:::ordered_block id=sequence
steps:
  - id: send_hello

    action: utter_hello
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
