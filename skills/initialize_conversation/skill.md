---
name: Initialize Conversation
description: >
  Starts every conversation, and resolves the precondition membership_known. It loads the
  signed-in member's record into project memory, then greets. A signed-in member is greeted by
  first name and asked nothing. A visitor is asked whether they are a member or shopping for a
  plan, and which plan they ask about. Run again as the resolver of the precondition, it skips
  the greeting and asks only what is still unknown.
hidden: true

# Block-only tools: the gate is open only while the block runs them, so the model is never offered them.
tool_constraints:
  - load_member_record:
      requires: "session.initialize_conversation.tool_gate_open"
  - remember_pending_request:
      requires: "session.initialize_conversation.tool_gate_open"
  - store_opener_replies:
      requires: "session.initialize_conversation.tool_gate_open"
---

:::ordered_block id=sequence
steps:
  - id: initial_run

    noop: true
    next:
      - if: "session.project.opener_done"
        then: unlock_store

      - else: unlock_fetch

  # First run: load the member record, then greeting.
  - id: unlock_fetch

    set_memory:
      tool_gate_open: true
    next: fetch

  - id: fetch

    execute_tool: load_member_record
    next: relock_fetch

  - id: relock_fetch

    set_memory:
      tool_gate_open: false
    next: say_hello_first

  - id: say_hello_first

    action: utter_greet_member
    next: require_member_status

  # A later run, as the precondition's resolver: the member's latest message is the parked
  # request. Save it, so the parked skill can still route it after the questions.
  - id: unlock_store

    set_memory:
      tool_gate_open: true
    next: store

  - id: store

    execute_tool: remember_pending_request
    next: relock_store

  - id: relock_store

    set_memory:
      tool_gate_open: false
    next: require_member_status

  # A closed question with an `unclear` option: an answer that names no option is asked again.
  - id: require_member_status

    noop: true
    next:
      - if: >-
          not session.project.membership and (not session.initialize_conversation.membership_reply
          or session.initialize_conversation.membership_reply == 'unclear')
        then: wipe_membership

      - else: require_plan_type

  - id: wipe_membership

    set_memory:
      membership_reply: null
    next: prompt_member_status

  - id: prompt_member_status

    collect: membership_reply
    utterance: utter_ask_membership
    next:
      - if: "session.initialize_conversation.membership_reply == 'unclear'"
        then: wipe_membership

      - else: require_plan_type

  - id: require_plan_type

    noop: true
    next:
      - if: >-
          session.project.plan_type or (session.initialize_conversation.plan_reply
          and session.initialize_conversation.plan_reply != 'unclear')
        then: unlock_store_replies

      - else: reset_plan_type

  - id: reset_plan_type

    set_memory:
      plan_reply: null
    next: prompt_plan_type

  - id: prompt_plan_type

    collect: plan_reply
    utterance: utter_ask_plan
    next:
      - if: "session.initialize_conversation.plan_reply == 'unclear'"
        then: reset_plan_type

      - else: unlock_store_replies

  # Copy the visitor's answers to project memory, where the precondition reads them.
  - id: unlock_store_replies

    set_memory:
      tool_gate_open: true
    next: store_replies

  - id: store_replies

    execute_tool: store_opener_replies
    next: relock_store_replies

  # A question in this run: end here, so session start can say how it can help, or the parked
  # skill can start. Nothing asked: the turn waits for the member's first question.
  - id: relock_store_replies

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.initialize_conversation.plan_reply"
        then: END

      - else: await_member

  - id: await_member

    action: action_listen
    next: END

:::
