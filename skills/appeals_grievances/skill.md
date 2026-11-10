---
name: Appeals and Complaints
description: >
  Appeals and complaints - how to appeal a denied service, drug or payment, how long an appeal
  takes, and how to file a complaint (grievance) about care, a provider, waiting times or our
  service. For example "How do I appeal a denial?", "My surgery was denied, what can I do?", "I want
  to file a complaint about my doctor's office" or "Your service is terrible". Not the status of a
  claim or an authorization (those topics).
precondition: membership_known

# A prose skill with blocks. Each block sets `routed`, and the skill completes on that condition.
complete_when:
  condition: "session.appeals_grievances.handled"
---

The member wants to appeal a decision, or to complain. Invoke the block that fits:
- @block.appeal: the member disagrees with a denial of a service, a drug or a payment, or asks how to appeal.
- @block.grievance: the member is unhappy with the care, a provider, waiting times, or our service, and wants to complain.
- @block.ask_type: the member says only "I want to file something" or "I have a problem", and it is not clear which one.

Invoke one block at a time. The blocks send the texts themselves: never answer in your own words here, and never say whether an appeal will succeed.

:::ordered_block id=ask_type
steps:
  - id: prompt

    action: utter_ask_appeal_or_grievance
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=appeal
steps:
  - id: mark

    set_memory:
      kind: appeal
      handled: true
    next: send

  - id: send

    action: utter_appeal_rules
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::

:::ordered_block id=grievance
steps:
  - id: mark

    set_memory:
      kind: grievance
      handled: true
    next: send

  - id: send

    action: utter_grievance_rules
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::
