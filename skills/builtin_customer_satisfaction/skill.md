---
name: Satisfaction Rating
description: "Asks how the conversation was (csat_score), thanks the member, then ends the chat."
routing:
  engine_managed: true

# Block-only tool: the gate is open only while the block runs it.
tool_constraints:
  - close_chat:
      requires: "session.builtin_customer_satisfaction.tool_gate_open"
---

:::ordered_block id=sequence
name: builtin_customer_satisfaction
steps:
  # The question opens its gate first. The post-write tool rolls back a rating that was written
  # before the member answered this question.
  - id: unlock_score

    set_memory:
      csat_score: null
      csat_score_question_open: true
    next: prompt_score

  - id: prompt_score

    collect: csat_score
    utterance: utter_ask_rating
    ask_before_filling: true
    description: "Record satisfied or unsatisfied from the member's rating of the conversation."
    next: send_gratitude

  - id: send_gratitude

    action: utter_thanks_for_rating
    next: unlock_finish

  - id: unlock_finish

    set_memory:
      tool_gate_open: true
    next: close_out

  - id: close_out

    execute_tool: close_chat
    next: relock_finish

  - id: relock_finish

    set_memory:
      tool_gate_open: false
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
