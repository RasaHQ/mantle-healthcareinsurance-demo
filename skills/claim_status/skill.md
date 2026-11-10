---
name: Claim Status
description: >
  Claims and Explanation of Benefits (EOB) - the status of the member's claims, whether a claim was
  paid, is still processing or was denied, what the plan paid and what the member owes, and why a
  claim was denied. Also a summary of the member's claims and follow-up questions about them. For
  example "Has my MRI claim been paid?", "Why do I owe $125?", "What does my EOB mean?" or "Why was my
  physical therapy claim denied?". Not whether a service is covered (the medical benefit topic) and
  not prior authorizations (the prior authorization topic).
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about their claims from my_claims, or sent the sign-in text, during this skill run."

# The lookup is block-only. The answer tool is offered only after the lookup ran.
tool_constraints:
  - load_claims:
      requires: "session.claim_status.tool_gate_open"
  - my_claims:
      requires: "session.claim_status.claims_loaded"
---

Help the member understand their claims.

Invoke @block.sequence once, for the first question about claims in this skill run. Do not invoke it again in the same skill run.

When the block ends without a reply, and for every later question about the claims, call @tool.my_claims and answer exactly the member's question (current_question in its result) from it, in one to three short sentences. For a question about one claim, answer about that claim only. Give what the plan paid and what the member owes when the result has them. For a denied claim, give the reason and the next step from the result.

:::ordered_block id=sequence
steps:
  - id: unlock

    set_memory:
      tool_gate_open: true
    next: fetch

  - id: fetch

    execute_tool: load_claims
    next: seal

  - id: seal

    set_memory:
      tool_gate_open: false
    next:
      - if: "session.claim_status.claims_loaded"
        then: END

      - else: send_sign_in

  # Not signed in: no claims to look up.
  - id: send_sign_in

    action: utter_sign_in_for_member_data
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
