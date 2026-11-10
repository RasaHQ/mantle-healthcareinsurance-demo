---
name: Login Help
description: >
  The member website and app - the member cannot sign in, forgot their password, is locked out,
  wants to create an account, or wants a family member or caregiver to access their account. For
  example "I forgot my password", "My account is locked", "How do I register?" or "Can my daughter
  log in for me?".
---

The member has a question about signing in. Each block sends the authored answer for one case. Invoke the block of the member's case:
- @block.forgot_password: the member forgot their password, or the password does not work.
- @block.locked_out: the member's account is locked, or they got a message that it is blocked after too many tries.
- @block.register: the member wants to create an account.
- @block.family_login: a family member, caregiver or other person wants to access the account or talk for the member.
- @block.login_general: any other sign-in question, or the member does not say what the problem is.

Invoke one block at a time. The blocks send the answers themselves: never answer in your own words here.

:::ordered_block id=forgot_password
steps:
  - id: send

    action: utter_forgot_password
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=locked_out
steps:
  - id: send

    action: utter_locked_out
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=register
steps:
  - id: send

    action: utter_register
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=family_login
steps:
  - id: send

    action: utter_family_login
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::

:::ordered_block id=login_general
steps:
  - id: send

    action: utter_login_general
    next: await_member

  - id: await_member

    action: action_listen
    next: END

:::
