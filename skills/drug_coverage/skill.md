---
name: Drug Coverage
description: >
  Prescription drugs (Part D) - whether a drug is on the plan's drug list (formulary), its tier,
  what it costs at a pharmacy or by mail order, and whether it needs prior authorization, step
  therapy or has a quantity limit. Also the yearly cap on drug costs, insulin costs, preferred
  pharmacies and mail order. For example "Is Eliquis covered?", "What tier is metformin?", "How do
  I get my drugs by mail?" or "Why does my insulin cost more?". Not the status of a drug coverage
  request (the prior authorization topic).
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about a drug from the result of check_drug, or about pharmacies from pharmacy_facts, during this skill run."
---

Help the member with their prescription drugs. The member's plan comes from their session.

When the member asks about a drug, call @tool.check_drug with the drug name as the member says it (a brand name or a generic name) and the strength when they give it. When the member names no drug, ask which drug they mean. Ask for the strength only when the result says that the strength matters for the answer (strength_covered is false).

When the member asks about pharmacies, mail order, the yearly cap or paying drug costs over the year, call @tool.pharmacy_facts.

Answer only from the tool result. Give the tier and the cost at a preferred pharmacy for a 30-day supply, and the mail-order cost when the member asks about it. Say when the drug needs prior authorization or step therapy, or has a quantity limit, and give the detail from the result. For a drug that is not on the drug list, give the next_step from the result. Never advise the member to start, stop or change a drug.
