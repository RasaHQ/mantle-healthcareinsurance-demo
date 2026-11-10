---
name: Change PCP Confirm
description: >
  The PCP change - says which doctor becomes the member's PCP and from when, asks the member to
  continue, asks them to confirm, then makes the change. Linked by change_pcp only.
hidden: true

# Block-only tools. The change also requires both of the member's yes answers, so it cannot run from
# any other path, also not from the block when an answer is missing.
tool_constraints:
  - prepare_pcp_change:
      requires: "session.change_pcp_confirm.tool_gate_open"
  - submit_pcp_change:
      requires: >-
        session.change_pcp_confirm.tool_gate_open
        and session.change_pcp_confirm.proceed_reply == 'yes'
        and session.change_pcp_confirm.confirm_reply == 'yes'
        and not session.change_pcp_confirm.change_reference
---

:::ordered_block id=sequence
steps:
  - id: unlock_ready

    set_memory:
      tool_gate_open: true
    next: ready

  - id: ready

    execute_tool: prepare_pcp_change
    next: relock_ready

  - id: relock_ready

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.change_pcp_confirm.new_pcp_name"
        then: send_change

      - else: send_failure

  # First question: continue? A closed question with a gate and one retry. A no, or a second
  # unclear answer, ends the change.
  - id: send_change

    action: utter_pcp_change_summary
    next: begin_proceed

  - id: begin_proceed

    set_memory:
      reasked: null
    next: unlock_proceed

  - id: unlock_proceed

    set_memory:
      proceed_reply: null
      proceed_reply_question_open: true
    next: prompt_proceed

  - id: prompt_proceed

    collect: proceed_reply
    ask_before_filling: true
    utterance: utter_ask_pcp_continue
    next:
      - if: "session.change_pcp_confirm.proceed_reply == 'yes'"
        then: begin_confirmation

      - if: "session.change_pcp_confirm.proceed_reply == 'no' or session.change_pcp_confirm.reasked"
        then: send_kept

      - else: reprompt_proceed

  - id: reprompt_proceed

    set_memory:
      reasked: true
    next: unlock_proceed

  # Second question: confirm. The same rules.
  - id: begin_confirmation

    set_memory:
      reasked: null
    next: unlock_confirmation

  - id: unlock_confirmation

    set_memory:
      confirm_reply: null
      confirm_reply_question_open: true
    next: prompt_confirmation

  - id: prompt_confirmation

    collect: confirm_reply
    ask_before_filling: true
    utterance: utter_ask_pcp_confirm
    next:
      - if: "session.change_pcp_confirm.confirm_reply == 'yes'"
        then: unlock_commit

      - if: "session.change_pcp_confirm.confirm_reply == 'no' or session.change_pcp_confirm.reasked"
        then: send_kept

      - else: reprompt_confirmation

  - id: reprompt_confirmation

    set_memory:
      reasked: true
    next: unlock_confirmation

  - id: unlock_commit

    set_memory:
      tool_gate_open: true
    next: commit

  - id: commit

    execute_tool: submit_pcp_change
    next: relock_commit

  - id: relock_commit

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.change_pcp_confirm.change_reference"
        then: send_done

      - else: send_failure

  - id: send_done

    action: utter_pcp_change_done
    next: END

  - id: send_kept

    action: utter_pcp_change_kept
    next: END

  - id: send_failure

    action: utter_pcp_change_error
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::
