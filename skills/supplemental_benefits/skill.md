---
name: Extra Benefits
description: >
  Extra benefits of the plan - dental, vision (eye exams, glasses, contacts), hearing exams and
  hearing aids, the over-the-counter (OTC) allowance and benefits card, the gym and fitness
  benefit, rides to appointments, and meals after a hospital stay. For example "Does my plan cover
  dental?", "How much is left on my OTC card?", "Does my plan pay for hearing aids?" or "Can I get a
  ride to my doctor?". Not medical services such as specialist visits or scans (the medical benefit
  topic), and not drugs (the drug topic).
precondition: membership_known

complete_when:
  criteria:
    - "The assistant sent a reply that answers the member's question about an extra benefit from extra_benefit_facts, during this skill run."

# The note tool is block-only. The facts tool is offered only after the block noted the texts.
tool_constraints:
  - note_benefit_text:
      requires: "session.supplemental_benefits.tool_gate_open"
  - extra_benefit_facts:
      requires: "session.supplemental_benefits.facts_ready"
---

Help the member with the extra benefits of their plan.

Invoke @block.sequence once, for the first question about extra benefits in this skill run. Do not invoke it again in the same skill run.

The block sends no answer of its own. When the block ends, call @tool.extra_benefit_facts and answer exactly the member's question (current_question in its result) from it, in one to three short sentences. For a later question about extra benefits, call @tool.extra_benefit_facts again and answer from it.

:::ordered_block id=sequence
steps:
  # The engine picks the variant of each text for the member's plan. The texts are noted for
  # extra_benefit_facts, not sent.
  - id: unlock

    set_memory:
      tool_gate_open: true
      facts_ready: true
    next: note_dental

  - id: note_dental

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_dental
    next: note_vision

  - id: note_vision

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_vision
    next: note_hearing

  - id: note_hearing

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_hearing
    next: note_otc

  - id: note_otc

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_otc
    next: note_fitness

  - id: note_fitness

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_fitness
    next: note_rides

  - id: note_rides

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_transportation
    next: note_meals

  - id: note_meals

    execute_tool: note_benefit_text
    parameters:
      response: utter_benefit_meals
    next: seal

  - id: seal

    set_memory:
      tool_gate_open: false
    next: END

:::
