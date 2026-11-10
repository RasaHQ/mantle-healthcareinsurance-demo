---
name: Change PCP
description: >
  Changing the member's primary care provider (PCP) - the member wants a new PCP, wants to switch
  doctors, or wants to make a doctor their PCP. For example "I want to change my primary care
  doctor", "Can I switch my PCP to Dr. Kim?" or "Make Dr. Brooks my doctor". Not finding a
  specialist (the find a provider topic).
precondition: membership_known

# The confirmation skill makes the change. This skill only picks the doctor, so it completes when
# the member picked one or when nobody is signed in.
complete_when:
  condition: "session.change_pcp.handled"

# The pick is offered only to a signed-in member.
tool_constraints:
  - pick_new_pcp:
      requires: "session.project.member_id"
---

Help a signed-in member pick a new primary care provider. Never change the PCP in your own words: the change happens only after the member confirms it twice.

Invoke @block.sign_in when the person is not signed in.

When the member names a doctor, call @tool.pick_new_pcp with that name. When the member names no doctor, ask which doctor they want; they can also ask you to find a family medicine or internal medicine doctor near their ZIP code. When the result says the doctor can be the member's PCP, invoke @block.confirm. When it says the doctor cannot (not in network, not a primary care doctor, or not accepting new patients), say why, from the result, and ask whether they want another doctor.

:::ordered_block id=confirm
steps:
  - id: mark

    set_memory:
      handled: true
    next: go_confirmation

  - id: go_confirmation

    link: change_pcp_confirm
:::

:::ordered_block id=sign_in
steps:
  - id: mark

    set_memory:
      handled: true
    next: send

  - id: send

    action: utter_sign_in_for_member_data
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
