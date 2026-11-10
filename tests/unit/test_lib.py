"""Unit tests of lib/. Run from the repository root: python -m pytest tests/unit -q"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib import question_gate, conversation_events, member_data, service_hours  # noqa: E402


# Small stand-ins for the engine's events and tool context. The lib code reads only the class
# name and a few attributes, so these classes carry the same names.
@dataclass
class UserUttered:
    text: str


@dataclass
class MemorySet:
    key: str
    value: Any


@dataclass
class SkillActivated:
    skill_id: str


@dataclass
class FakeMemory:
    values: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str) -> Any:
        return self.values.get(key)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value


@dataclass
class FakeContext:
    events: list[Any] = field(default_factory=list)
    memory: FakeMemory = field(default_factory=FakeMemory)


# --- member_data -------------------------------------------------------------------------------


def _context_for(member_id: str | None = None, **memory: Any) -> FakeContext:
    values = {"project.member_id": member_id} if member_id else {}
    values.update({f"project.{k}": v for k, v in memory.items()})
    return FakeContext(memory=FakeMemory(values))


def test_member_record_comes_from_the_session_id_only():
    assert member_data.member_record(_context_for("m1001"))["first_name"] == "Alex"
    assert member_data.member_record(_context_for()) is None


def test_plan_comes_from_the_member_or_from_the_visitor_answer():
    assert member_data.plan_id(_context_for("m1002")) == "ppo"
    assert member_data.plan_id(_context_for(plan_type="hmo")) == "hmo"
    assert member_data.plan_id(_context_for(plan_type="not_sure")) is None


def test_claims_and_authorizations_need_a_signed_in_member():
    dates = [claim["service_date"] for claim in member_data.member_claims(_context_for("m1001"))]
    assert dates == sorted(dates, reverse=True)
    assert member_data.member_claims(_context_for()) is None
    assert member_data.authorizations(_context_for()) is None


def test_check_services_by_code_and_category():
    result = member_data.check_services(["70551", "99999"], ["specialist", "skydiving"], "hmo")
    assert result["unknown_codes"] == ["99999"]
    assert result["unknown_categories"] == ["skydiving"]
    mri, specialist = result["results"]
    assert mri["prior_authorization_required"] is True and mri["you_pay"].startswith("$250")
    assert specialist["referral_required"] is True


def test_check_services_without_a_plan_gives_each_plan():
    result = member_data.check_services([], ["specialist"], None)
    by_plan = result["results"][0]["by_plan"]
    assert by_plan["Rasa Advantage PPO"]["referral_required"] is False
    assert by_plan["Rasa Advantage HMO"]["referral_required"] is True


def test_check_drug_by_brand_name_and_rules():
    result = member_data.check_drug("Eliquis", "5 mg", "hmo")
    assert result["drug"] == "apixaban" and result["tier"] == 3 and result["strength_covered"] is True
    assert result["preferred_retail_30_day"] == "$47"
    assert member_data.check_drug("Ozempic", "", "ppo")["prior_authorization_required"] is True


def test_insulin_cap_and_excluded_and_unknown_drugs():
    assert "$35" in member_data.check_drug("Lantus", "", "hmo")["cost"]
    assert member_data.check_drug("Viagra", "", "hmo")["excluded_by_law"] is True
    unknown = member_data.check_drug("madeupzumab", "", "hmo")
    assert unknown["on_drug_list"] is False and "exception" in unknown["next_step"]


def test_find_providers_by_name_and_network():
    result = member_data.find_providers("", "", "Dr. Patel", "hmo")
    networks = {p["name"]: p["in_network_for_your_plan"] for p in result["providers"]}
    assert networks == {"Dr. Maya Patel": True, "Dr. Robert Patel": False}
    assert member_data.find_providers("astrology", "", "", "hmo")["unknown_specialty"] is True


def test_out_of_pocket_against_the_limits():
    costs = member_data.out_of_pocket(_context_for("m1002"))
    assert costs["medical_left_until_max"] == "$1,000"
    assert costs["drug_cap_reached"] is True
    assert member_data.out_of_pocket(_context_for()) is None


# --- question_gate ----------------------------------------------------------------------------------


def test_an_answer_after_the_gate_opened_counts():
    events = [MemorySet("member_services_handoff.consent_reply_question_open", True), UserUttered("yes")]
    assert question_gate.answered_after_opening(FakeContext(events), "member_services_handoff.consent_reply_question_open")


def test_an_answer_before_the_gate_opened_does_not_count():
    events = [UserUttered("yes, and also ..."), MemorySet("member_services_handoff.consent_reply_question_open", True)]
    assert not question_gate.answered_after_opening(FakeContext(events), "member_services_handoff.consent_reply_question_open")


def test_a_newer_question_takes_the_answer():
    events = [
        MemorySet("member_services_handoff.consent_reply_question_open", True),
        MemorySet("resolution_question.resolved_reply_question_open", True),
        UserUttered("no"),
    ]
    assert not question_gate.answered_after_opening(FakeContext(events), "member_services_handoff.consent_reply_question_open")


# --- service_hours -----------------------------------------------------------------------------


def test_hours_profile_overrides_the_clock():
    assert service_hours.member_services_open(FakeContext(memory=FakeMemory({"project.hours_profile": "always_open"})))
    assert not service_hours.member_services_open(FakeContext(memory=FakeMemory({"project.hours_profile": "never_open"})))


def test_opening_hours_follow_the_season():
    tz = service_hours.TIMEZONE
    context = FakeContext()
    assert service_hours.member_services_open(context, datetime(2026, 11, 15, 10, 0, tzinfo=tz))  # Sunday in November
    assert not service_hours.member_services_open(context, datetime(2026, 5, 17, 10, 0, tzinfo=tz))  # Sunday in May
    assert service_hours.member_services_open(context, datetime(2026, 5, 18, 10, 0, tzinfo=tz))  # Monday in May
    assert not service_hours.member_services_open(context, datetime(2026, 11, 26, 10, 0, tzinfo=tz))  # Thanksgiving
    assert not service_hours.member_services_open(context, datetime(2026, 11, 16, 21, 0, tzinfo=tz))  # after 8 p.m.


def test_hours_text_uses_us_times():
    assert "8 a.m. to 8 p.m. Eastern Time" in service_hours.hours_text()


# --- conversation_events -----------------------------------------------------------------------


def test_declines_in_a_row_stop_at_a_topic():
    events = [
        UserUttered("is my drug covered?"), SkillActivated("drug_coverage"),
        UserUttered("weather?"), SkillActivated("builtin_unsupported_request_handler"),
        UserUttered("football?"), SkillActivated("builtin_unsupported_request_handler"),
    ]
    assert conversation_events.decline_streak(FakeContext(events)) == 2


def test_last_topic_skips_the_engine_skills():
    events = [SkillActivated("claim_status"), SkillActivated("builtin_completed"), SkillActivated("representative_request")]
    assert conversation_events.last_topic(FakeContext(events)) == "claim_status"
