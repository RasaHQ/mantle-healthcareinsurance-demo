---
name: Out-of-Pocket Costs
description: >
  The member's costs for the year - the monthly premium and how it is paid, the maximum
  out-of-pocket limit and how much is left before the member reaches it, and the yearly cap on
  drug costs. For example "How close am I to my out-of-pocket max?", "What's my premium?", "How is
  my premium paid?" or "Have I hit the drug cap yet?". Not the cost of one service (the medical
  benefit topic) or one drug (the drug topic).
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about their costs from my_costs, during this skill run."
---

Help the member with their costs for the year.

Call @tool.my_costs and answer exactly the member's question (current_question in its result) from its result, in one to three short sentences. For a person who is not signed in, the result has the plan's limits but no spending: give the limits, and say that the member can log in to see how much they have spent.
