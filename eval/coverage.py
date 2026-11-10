"""Which paths of the assistant have an eval, and which do not.

Every path has an id, for example `id.wrong_address` or `drug.step_therapy`. An e2e test case
covers a path when its name starts with `[<id>]`; a scenario covers a path when its `name` starts
with `[<id>]`. PATHS below is the list of all paths: add an id here when you add a path to a skill.

    python -m eval.coverage            # the uncovered paths, and a summary per area
    python -m eval.coverage --all      # every path with its e2e cases and scenarios
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths that no conversation can reach on purpose: they need a back-end failure or a clock change.
NOT_REACHABLE = {
    "confirm.prepare_failure": "prepare_pcp_change finds no member record or no picked doctor",
    "confirm.submit_failure": "submit_pcp_change refuses after both answers",
    "handoff.hours_changed_at_transfer": "the hours change between the availability check and the transfer",
    "handoff.real_clock": "the real opening hours, holidays and seasons (unit tests cover them)",
}

PATHS = """
init.member_greeted init.visitor_buttons init.visitor_typed init.visitor_not_sure init.membership_unclear_retry
init.plan_unclear_retry init.both_answers_in_one_msg init.parked_request init.unknown_seeded_id init.non_topic_at_opener
init.correction
wrapup.no wrapup.yes_extra_help wrapup.yes_with_task wrapup.unclear wrapup.unhandled_new_message wrapup.silent_after_handoff
csat.unsatisfied csat.typed csat.rating_before_question csat.message_after_chat_ended
res.yes res.no_open res.no_closed res.unclear_retry res.unclear_twice
farewell.yes farewell.no thanks.already_over
resume.yes resume.no resume.discard_after_handoff resume.discard_after_close
decline.out_of_domain decline.in_domain decline.part_b_amount decline.refill decline.appointment decline.streak3_yes
decline.streak3_no decline.streak3_closed decline.streak_reset_by_topic decline.after_decline_hook
rep.ask rep.earlier_topic rep.closed rep.visitor
topic.named topic.person_again topic.unclear_once topic.unclear_twice
handoff.yes_button handoff.yes_typed handoff.no handoff.unclear_retry handoff.unclear_twice handoff.yes_before_question
handoff.stale_consent_button handoff.visitor_name handoff.visitor_refuses_name handoff.reentry_after_transfer
handoff.closed.grievance handoff.closed.appeal handoff.closed.benefit_decision handoff.closed.enroll_leave
handoff.closed.enroll_moving handoff.closed.enroll_medicaid handoff.closed.language handoff.closed.id_wrong_address
handoff.closed.prior_auth_appeal
benefit.hmo_specialist_referral benefit.code benefit.multi_code benefit.unknown_code benefit.unknown_category
benefit.ppo_in_network benefit.ppo_oon benefit.shopper_by_plan benefit.shopper_single_plan benefit.ask_once benefit.ask_twice
benefit.ask_cap benefit.to_rep benefit.non_covered benefit.acupuncture_rule benefit.emergency
drug.covered_brand drug.generic_name drug.mail_order drug.pa drug.step_therapy drug.quantity_limit drug.tier4 drug.specialty
drug.insulin drug.excluded drug.unknown drug.no_drug_named drug.strength_ok drug.strength_not_covered
drug.new_member_transition drug.pharmacy_facts drug.payment_plan drug.shopper_by_plan drug.cap_question drug.typo
provider.name_not_in_network provider.own_pcp provider.specialty_zip provider.no_criteria provider.unknown_specialty
provider.language provider.not_accepting provider.ambiguous_name provider.no_match provider.visitor_my_pcp
provider.then_change_pcp
pcp.yes_yes pcp.typed_yes_yes pcp.yes_no pcp.no_first pcp.unclear_retry pcp.unclear_twice_first pcp.unclear_twice_confirm
pcp.gate_early_yes pcp.specialist pcp.not_in_network_hmo pcp.not_in_network_ppo pcp.not_accepting pcp.already_pcp
pcp.multiple_usable pcp.not_in_directory pcp.no_name pcp.retry_another_doctor pcp.visitor_sign_in pcp.digression
id.web_yes id.typed_yes id.app_variant id.wrong_address id.typed_new_address id.unclear_retry id.unclear_twice
id.invalid_payload id.visitor id.red_white_blue_card
claim.denied claim.denied_owes claim.denied_cosmetic claim.paid claim.processing claim.summary claim.visitor
claim.other_member_claim_id claim.other_member_by_name claim.other_member_by_member_id claim.paid_eob
auth.pending_medical auth.no_prediction auth.pending_partd auth.approved auth.denied auth.appeal_to_rep auth.none
auth.visitor
oop.moop_progress oop.ppo_combined_max oop.drug_cap_reached oop.moop_reached oop.hmo_no_premium
oop.premium_payment_method oop.visitor_limits oop.shopper_not_sure oop.part_b
extras.otc_ppo extras.otc_hmo extras.otc_zero extras.otc_visitor extras.dental_hmo extras.dental_ppo extras.dental_not_sure
extras.vision_hmo extras.vision_ppo extras.hearing extras.fitness extras.rides_hmo extras.rides_ppo extras.meals
enroll.switch_callback_yes callback.no callback.unclear callback.invalid_phone enroll.leave enroll.moving enroll.medicaid
enroll.open_enrollment_question enroll.reason_once enroll.reason_twice enroll.reason_cap enroll.shopper enroll.cancel_now
appeals.appeal appeals.grievance appeals.ask_type appeals.visitor
login.forgot_app login.forgot_web login.locked login.register_web login.register_app login.family login.general
greeting.member greeting.visitor bot abuse abuse.with_question medical_advice language.open language.spanish
x.multi_intent_drug_costs x.multi_intent_claim_auth x.multi_intent_card_pcp x.digression_resume_no
x.digression_unclear_resume x.yes_with_new_request x.phone_correction x.spanish x.profanity x.long_message
x.emoji_and_typos
adv.instruction_override adv.non_formulary_price adv.internals adv.injection_in_drug_name adv.fake_system_text
adv.phi_by_name adv.set_member_id adv.force_transfer_flag adv.cancel_by_prompt adv.no_unrequested_transfer
""".split()

_ID = re.compile(r"""(?:test_case|name):\s*["']?\[([^\]]+)\]""")


def eval_ids() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Path id -> e2e files, and path id -> scenario files."""
    e2e: dict[str, list[str]] = defaultdict(list)
    scenarios: dict[str, list[str]] = defaultdict(list)
    for path in sorted((REPO_ROOT / "tests" / "e2e").glob("*.yml")):
        for found in _ID.findall(path.read_text()):
            e2e[found].append(path.name)
    for path in sorted((REPO_ROOT / "eval" / "scenarios").glob("*/*.yml")):
        for found in _ID.findall(path.read_text()):
            scenarios[found].append(f"{path.parent.name}/{path.name}")
    return e2e, scenarios


def area(path_id: str) -> str:
    return path_id.split(".")[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="list every path with its evals")
    args = parser.parse_args()
    e2e, scenarios = eval_ids()
    uncovered = [p for p in PATHS if p not in e2e and p not in scenarios]
    unknown = sorted((set(e2e) | set(scenarios)) - set(PATHS))
    per_area: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for p in PATHS:
        per_area[area(p)][0] += 1
        per_area[area(p)][1] += p in e2e or p in scenarios
    if args.all:
        for p in PATHS:
            print(f"{p:42} e2e: {len(e2e.get(p, []))}  scenarios: {', '.join(scenarios.get(p, [])) or '-'}")
        print()
    print(f"{'area':12} paths  covered")
    for name, (total, covered) in sorted(per_area.items()):
        print(f"{name:12} {total:5}  {covered:7}")
    print(f"\n{len(PATHS)} paths, {len(PATHS) - len(uncovered)} covered, {len(uncovered)} uncovered.")
    print(f"Not reachable on purpose ({len(NOT_REACHABLE)}): " + ", ".join(NOT_REACHABLE))
    for p in uncovered:
        print(f"UNCOVERED {p}")
    for p in unknown:
        print(f"UNKNOWN ID {p}: an eval names a path that is not in PATHS")
    return 1 if uncovered or unknown else 0


if __name__ == "__main__":
    sys.exit(main())
