---
name: Prior Authorization Status
description: >
  Prior authorizations and drug coverage requests - whether a request for a service or a drug was
  approved, is still pending, or was denied, when a decision is due, and why a request was
  denied. For example "Has my MRI been approved?", "What's happening with my knee surgery
  approval?" or "Did my doctor's request for Ozempic go through?". Not claims (the claim topic).
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about their authorizations from authorizations_on_record, or sent the sign-in text, during this skill run."

# The lookup is block-only. The answer tool is offered only after the lookup ran.
tool_constraints:
  - load_authorizations:
      requires: "session.prior_auth_status.tool_gate_open"
  - authorizations_on_record:
      requires: "session.prior_auth_status.loaded"
---

Help the member find out where their prior authorizations and drug coverage requests are.

Invoke @block.sequence once, for the first question in this skill run. Do not invoke it again in the same skill run.

When the block ends without a reply, and for every later question, call @tool.authorizations_on_record and answer exactly the member's question (current_question in its result) from it, in one to three short sentences. For a pending request, give the date by which a decision is due. For a denied request, give the reason and the next step from the result. Never say whether a pending request will be approved.

When the member wants help with an appeal, invoke @block.to_representative.

:::ordered_block id=sequence
steps:
  - id: unlock

    set_memory:
      tool_gate_open: true
    next: fetch

  - id: fetch

    execute_tool: load_authorizations
    next: seal

  - id: seal

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.prior_auth_status.loaded"
        then: END

      - else: send_sign_in

  - id: send_sign_in

    action: utter_sign_in_for_member_data
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=to_representative
steps:
  - id: go_transfer

    call: member_services_handoff
    next: END

:::
