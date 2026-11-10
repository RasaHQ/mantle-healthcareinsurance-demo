---
name: Representative Topic
description: >
  The topic question after a request for a person - the member asked for a person and named no
  topic yet. The assistant asks what they need help with, and the topic's skill answers.
  Linked by representative_request only.
hidden: true
---

The member asked for a person. First ask what they need help with, so that the right skill or the right Member Services team can help. Never answer the member in your own words here.
- When the member's answer names a topic that this assistant helps with, start that topic's skill. For example "about my claim", "is my insulin covered?", "I lost my ID card".
- Invoke @block.prompt_topic to ask the question, and again when the member only asks for a person again, for example "Just put me through to someone".
- Invoke @block.topic_unclear when the answer names nothing that this assistant helps with, or that you cannot place, for example "about my car", "banana".

:::ordered_block id=prompt_topic
steps:
  - id: tally

    noop: true
    next:
      - if: "session.representative_topic.ask_count >= 1"
        then: prompt_repeat

      - else: prompt_initial

  - id: prompt_initial

    set_memory:
      ask_count: 1
    next: prompt

  - id: prompt_repeat

    set_memory:
      ask_count: 2
    next: prompt

  - id: prompt

    action: utter_ask_topic
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=topic_unclear
steps:
  # After the second answer that names no topic, offer a person.
  - id: tally

    noop: true
    next:
      - if: "session.representative_topic.ask_count >= 2"
        then: send_connect

      - else: prompt_repeat

  - id: prompt_repeat

    set_memory:
      ask_count: 2
    next: prompt

  - id: prompt

    action: utter_ask_topic
    next: await_member

  - id: await_member

    action: action_listen
    next: END

  - id: send_connect

    action: utter_representative_can_help
    next: go_transfer

  - id: go_transfer

    link: member_services_handoff
:::
