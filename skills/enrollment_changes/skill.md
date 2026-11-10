---
name: Enrollment Changes
description: >
  Changing or leaving the plan - switching to another plan, cancelling or disenrolling, going back
  to Original Medicare, a move to a new address outside the area, or a change because the member
  got Medicaid or Extra Help. Also when the member can change plans. For example "Can I switch
  plans?", "I want to cancel my plan", "I'm moving to Florida", "I just got Medicaid" or "When is
  open enrollment?". The assistant explains the rules; it never changes or ends an enrollment itself.
precondition: membership_known

# A prose skill with blocks. A `link:` or `call:` from a block does not end a prose skill, so each
# block sets `routed`, and the skill completes on that condition.
complete_when:
  condition: "session.enrollment_changes.handled"
---

The member wants to change or leave their plan, or asks when they can. The reason decides the block. Invoke the block of that reason:
- @block.switch_plan: the member wants another plan, or asks when they can change plans ("Can I switch to the PPO?", "When is open enrollment?").
- @block.leave_plan: the member wants to cancel, disenroll or go back to Original Medicare ("Cancel my plan", "I want out").
- @block.moving: the member moves, or moved, to a new address ("I'm moving to Florida").
- @block.medicaid_extra_help: the member got Medicaid or Extra Help, or lost it ("I just got Medicaid").
- @block.prompt_reason: the member wants a change but gives no reason, and an answer to the reason question that still gives none.

Invoke one block at a time. The blocks send the texts and ask the questions themselves: never answer the member in your own words here, and never say that the plan was changed or ended.

:::ordered_block id=prompt_reason
steps:
  - id: tally

    noop: true
    next:
      - if: "session.enrollment_changes.ask_count >= 2"
        then: cap

      - if: "session.enrollment_changes.ask_count == 1"
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

    action: utter_ask_enrollment_reason
    next: await_member

  - id: await_member

    action: action_listen
    next: END

  - id: cap

    set_memory:
      handled: true
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::

:::ordered_block id=switch_plan
steps:
  # During Open Enrollment a licensed agent can call the member about the options.
  - id: mark

    set_memory:
      reason: switch_plan
      handled: true
    next: send_periods

  - id: send_periods

    action: utter_enrollment_periods
    next: go_call_back

  - id: go_call_back

    call: agent_callback
    next: END

:::

:::ordered_block id=leave_plan
steps:
  - id: mark

    set_memory:
      reason: leave_plan
      handled: true
    next: send_exit

  - id: send_exit

    action: utter_enrollment_leave
    next: send_periods

  - id: send_periods

    action: utter_enrollment_periods
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::

:::ordered_block id=moving
steps:
  - id: mark

    set_memory:
      reason: moving
      handled: true
    next: send_moving

  - id: send_moving

    action: utter_enrollment_moving
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::

:::ordered_block id=medicaid_extra_help
steps:
  - id: mark

    set_memory:
      reason: medicaid_extra_help
      handled: true
    next: send_medicaid

  - id: send_medicaid

    action: utter_enrollment_medicaid
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::
