---
name: Benefit Check
description: >
  Medical benefits - whether a medical service is covered, what the member pays for it (copay or
  coinsurance), and whether it needs a referral or prior authorization, by service name or by the
  procedure code on a provider's estimate. For example "Is a colonoscopy covered?", "What's my copay
  for a specialist?", "Do I need a referral to see a cardiologist?" or "How much is an MRI?". Not
  dental, vision, hearing, the OTC allowance, gyms, rides or meals (the extra benefits topic); not
  drugs (the drug topic); and not the status of a claim or a prior authorization.
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about a medical service from the result of check_benefit, or offered a person, during this skill run."

# The lookup is offered only after a block recorded that the member named a service or a code.
tool_constraints:
  - check_benefit:
      requires: "session.benefit_check.service_given"
---

Help the member find out what a medical service costs on their plan. The member's plan comes from their session; never ask for a member ID.

Invoke the block that fits the member's message:
- @block.lookup: the member names one or more services or procedure codes, for example "a colonoscopy", "physical therapy", "an out-of-network specialist", "99213 and 70551". Then call @tool.check_benefit with the codes and the categories, and answer from its result.
- @block.ask_service: the member asks about their benefits but names no service and no code, for example "What does my plan cover?" or "Can you check a benefit for me?". Also when the answer to that question still names no service.
- @block.to_representative: the member wants a decision about their own case, for example whether the plan will approve a surgery, or disagrees with the result.

Answer only from the result of @tool.check_benefit. For a code in unknown_codes, say that you don't recognize that code. Say when a service needs prior authorization or a referral, and give the result's next_step.

:::ordered_block id=lookup
steps:
  - id: mark

    set_memory:
      service_given: true
    next: END

:::

:::ordered_block id=ask_service
steps:
  - id: tally

    noop: true
    next:
      - if: "session.benefit_check.ask_count >= 2"
        then: go_propose

      - if: "session.benefit_check.ask_count == 1"
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

    action: utter_ask_service
    next: await_member

  - id: await_member

    action: action_listen
    next: END

  - id: go_propose

    call: member_services_handoff
    next: END

:::

:::ordered_block id=to_representative
steps:
  - id: send_propose

    action: utter_benefit_offer_person
    next: go_transfer

  - id: go_transfer

    call: member_services_handoff
    next: END

:::
