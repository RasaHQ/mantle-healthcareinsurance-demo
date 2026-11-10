---
name: Medical Advice
description: >
  Medical advice - the member asks what to do about their health: whether to start, stop or change
  a medicine, what a symptom means, or which treatment is right. For example "Can I stop taking my
  blood thinner before surgery?", "Is this rash serious?" or "Should I get the knee surgery?". The
  assistant does not give medical advice; this skill sends the member to the right people. Not
  whether the plan covers, pays for or approves a service or a drug, for example "Will you approve
  my surgery?" (the medical benefit, drug and prior authorization topics).
---

:::ordered_block id=sequence
steps:
  - id: send

    action: utter_no_medical_advice
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
