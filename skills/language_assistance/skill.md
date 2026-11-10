---
name: Language Assistance
description: >
  Language and accessibility help - an interpreter, information in another language, a TTY line
  for people who are deaf or hard of hearing, or documents in large print or braille. For example
  "I need an interpreter", "Do you speak Spanish?", "What's your TTY number?" or "Can I get this in
  large print?".
---

:::ordered_block id=sequence
steps:
  - id: send

    action: utter_language_assistance
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::
