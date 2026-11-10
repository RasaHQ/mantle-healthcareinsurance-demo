---
name: Resume Question
description: "After a digression - asks whether to resume the interrupted task."
routing:
  engine_managed: true

# Block-only tool: the gate is open only while the block runs it.
tool_constraints:
  - drop_finished_opener:
      requires: "session.builtin_continue_interrupted.tool_gate_open"
---

:::ordered_block id=sequence
name: builtin_continue_interrupted
steps:
  # The member chose a person, or closed the conversation: drop the interrupted task without the
  # question. `wants_to_resume: false` makes the engine dismiss it.
  - id: after_relock

    noop: true
    next:
      - if: >-
          session.member_services_handoff.handoff_started or session.project.asked_for_representative
          or session.thanks_reply.closed_by_member or session.farewell.closed_by_member
        then: discard

      - else: unlock_discard

  - id: discard

    set_memory:
      wants_to_resume: false
    next: END

  # The precondition runs initialize_conversation again on top of an earlier run that a typed
  # question interrupted. Once the member is qualified, that earlier run has nothing left to ask.
  - id: unlock_discard

    set_memory:
      tool_gate_open: true
    next: discard_opener

  - id: discard_opener

    execute_tool: drop_finished_opener
    next: relock_discard

  - id: relock_discard

    set_memory:
      tool_gate_open: false
    next: prompt_resume

  - id: prompt_resume

    collect: wants_to_resume
    utterance: utter_ask_wants_to_resume
    description: "Does the member want to resume the task that was interrupted?"
:::
