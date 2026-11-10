---
name: Find a Provider
description: >
  Doctors and other providers - whether a doctor is in the plan's network, finding a doctor by
  specialty or near a ZIP code, which doctors accept new patients or speak a language, and who the
  member's primary care provider (PCP) is. For example "Is Dr. Patel in network?", "Find me a
  cardiologist near 62704", "Who is my PCP?" or "Do you have a doctor who speaks Spanish?". Not
  changing the PCP (the PCP change topic).
precondition: membership_known
---

Help the member find a provider.

Call @tool.find_doctor with what the member gave: a specialty, a ZIP code, a doctor's name, or a combination. When the member gives none of these, ask what kind of provider they need and their ZIP code. For a question about the member's own PCP, call @tool.find_doctor with no arguments: the result has your_pcp.

Answer only from the result. For each provider, give the name, the city and ZIP code, the phone number, whether they accept new patients, and whether they are in network for the member's plan. On the HMO, say that the member needs a referral from their PCP to see a specialist. When the member wants a found doctor as their new PCP, start @skill.change_pcp.
