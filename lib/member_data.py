"""The plan data and the member's data.

The member is looked up only by `project.member_id`, which the channel seeds at session start (see
memory.yml). No function here takes a member id from the conversation: a member who types another
member's id gets nothing for it.

The JSON files are loaded at import. The engine unpacks the model into a temporary folder, which
may be gone by the time a tool runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA = Path(__file__).parent / "data"


def _read_json(name: str) -> Any:
    return json.loads((_DATA / name).read_text())


PLANS: dict[str, Any] = _read_json("plans.json")
SERVICES: dict[str, Any] = _read_json("services.json")
FORMULARY: dict[str, Any] = _read_json("formulary.json")
PROVIDERS: dict[str, dict[str, Any]] = _read_json("providers.json")
MEMBERS: dict[str, dict[str, Any]] = _read_json("members.json")
CLAIMS: dict[str, list[dict[str, Any]]] = _read_json("claims.json")
AUTHORIZATIONS: dict[str, list[dict[str, Any]]] = _read_json("authorizations.json")

PLAN_IDS: tuple[str, ...] = tuple(PLANS["plans"])
CATEGORY_IDS: tuple[str, ...] = tuple(SERVICES["categories"])
SPECIALTIES: tuple[str, ...] = tuple(sorted({p["specialty"] for p in PROVIDERS.values()}))


# ---------------------------------------------------------------------------------------------
# The member


def member_id(context: Any) -> str | None:
    """The signed-in member's id from the session, or None for a visitor."""
    value = context.memory.get("project.member_id")
    return str(value) if value else None


def member_record(context: Any) -> dict[str, Any] | None:
    """The signed-in member's record, or None for a visitor or an unknown id."""
    key = member_id(context)
    return MEMBERS.get(key) if key else None


def plan_id(context: Any) -> str | None:
    """The member's plan, or the plan that a visitor asks about. None when that is not known."""
    record = member_record(context)
    if record:
        return record["plan"]
    value = context.memory.get("project.plan_type")
    return value if value in PLAN_IDS else None


def _plan_names(ids: tuple[str, ...] | list[str]) -> list[str]:
    return [PLANS["plans"][p]["name"] for p in ids]


def _by_plan(plan: str | None, value) -> dict[str, Any]:
    """`value(plan)` for one plan, or for each plan by name when the plan is not known."""
    if plan:
        return {"plan": PLANS["plans"][plan]["name"], **value(plan)}
    return {"by_plan": {PLANS["plans"][p]["name"]: value(p) for p in PLAN_IDS}}


def _records(store: dict[str, list[dict[str, Any]]], context: Any, key: str) -> list[dict[str, Any]] | None:
    member = member_id(context)
    if not member or member not in MEMBERS:
        return None
    return sorted(store.get(member, []), key=lambda r: r.get(key) or "", reverse=True)


def member_claims(context: Any) -> list[dict[str, Any]] | None:
    """The signed-in member's claims, newest first. None when nobody is signed in."""
    return _records(CLAIMS, context, "service_date")


def authorizations(context: Any) -> list[dict[str, Any]] | None:
    """The signed-in member's prior authorizations and drug coverage requests, newest first."""
    return _records(AUTHORIZATIONS, context, "submitted")


def provider_entry(provider_id: str | None) -> dict[str, Any] | None:
    return {"provider_id": provider_id, **PROVIDERS[provider_id]} if provider_id in PROVIDERS else None


def out_of_pocket(context: Any) -> dict[str, Any] | None:
    """The member's spending this year against the plan's maximum and the Part D cap."""
    record = member_record(context)
    if record is None:
        return None
    plan = PLANS["plans"][record["plan"]]
    moop = plan["max_out_of_pocket_in_network_amount"]
    cap = PLANS["program"]["part_d_out_of_pocket_cap_amount"]
    medical = record["medical_out_of_pocket_this_year"]
    drugs = record["drug_out_of_pocket_this_year"]
    return {
        "plan": plan["name"],
        "monthly_premium": plan["monthly_premium"],
        "premium_payment": record.get("premium_payment") or "No premium to pay on this plan.",
        "max_out_of_pocket": plan["max_out_of_pocket"],
        "medical_spent_this_year": f"${medical:,}",
        "medical_left_until_max": f"${max(moop - medical, 0):,}",
        "medical_max_reached": medical >= moop,
        **({"medical_left_until_combined_max": f"${max(plan['max_out_of_pocket_combined_amount'] - medical, 0):,}"}
           if plan.get("max_out_of_pocket_combined_amount") else {}),
        "drug_spent_this_year": f"${drugs:,}",
        "drug_left_until_cap": f"${max(cap - drugs, 0):,}",
        "drug_cap_reached": drugs >= cap,
        "part_d_out_of_pocket_cap": PLANS["program"]["part_d_out_of_pocket_cap"],
        "part_b_premium": PLANS["program"]["part_b_premium"],
    }


# ---------------------------------------------------------------------------------------------
# Lookups


def check_services(codes: list[str], categories: list[str], plan: str | None) -> dict[str, Any]:
    """What each service code and each category costs, and whether it needs prior authorization or
    a referral. Unknown codes and categories are listed separately, so the model never guesses them."""
    results, unknown_codes, unknown_categories = [], [], []
    wanted: list[tuple[str | None, str]] = []
    for code in codes:
        entry = SERVICES["codes"].get(code.strip().upper())
        if entry is None:
            unknown_codes.append(code)
        else:
            wanted.append((code.strip().upper(), entry["category"]))
    for category in categories:
        key = category.strip().lower()
        if key in SERVICES["categories"]:
            wanted.append((None, key))
        else:
            unknown_categories.append(category)
    for code, key in wanted:
        info = SERVICES["categories"][key]
        row: dict[str, Any] = {"service": info["label"]}
        if code:
            row.update(service_code=code, code_name=SERVICES["codes"][code]["name"])
        row["prior_authorization_required"] = info["prior_authorization_required"]
        if info.get("note"):
            row["note"] = info["note"]
        row.update(_by_plan(plan, lambda p, k=key: {
            "you_pay": PLANS["plans"][p]["medical"][k],
            "referral_required": SERVICES["categories"][k]["referral_required_hmo"] and p == "hmo",
        }))
        results.append(row)
    return {"results": results, "unknown_codes": unknown_codes, "unknown_categories": unknown_categories}


def _find_drug(name: str) -> tuple[str | None, dict[str, Any] | None, bool]:
    """(generic name, entry, excluded) for a generic or a brand name, or (None, None, False)."""
    wanted = name.strip().lower()
    for section, excluded in (("drugs", False), ("excluded_by_law", True)):
        for generic, entry in FORMULARY[section].items():
            if wanted == generic or wanted in (b.lower() for b in entry.get("brand_names", [])):
                return generic, entry, excluded
    return None, None, False


def check_drug(name: str, strength: str, plan: str | None) -> dict[str, Any]:
    """The formulary entry of a drug and its cost on the plan."""
    generic, entry, excluded = _find_drug(name)
    if entry is None:
        return {"drug": name, "on_drug_list": False, "next_step": FORMULARY["not_on_formulary_next_step"]}
    if excluded:
        return {"drug": generic, "on_drug_list": False, "excluded_by_law": True, "reason": entry["reason"]}
    tier = str(entry["tier"])
    result: dict[str, Any] = {
        "drug": generic,
        "brand_names": entry["brand_names"],
        "on_drug_list": True,
        "tier": int(tier),
        "strengths_covered": entry["strengths"],
        "prior_authorization_required": entry["prior_authorization"],
        "step_therapy": entry["step_therapy"],
        "quantity_limit": entry["quantity_limit"],
    }
    if strength:
        result["strength_asked"] = strength
        result["strength_covered"] = any(strength.replace(" ", "").lower() in s.replace(" ", "").lower() for s in entry["strengths"])
    for detail in ("prior_authorization_detail", "step_therapy_detail"):
        if entry.get(detail):
            result[detail] = entry[detail]
    if entry.get("specialty_pharmacy_only"):
        result["pharmacy"] = "Available only from our specialty pharmacy."

    def cost(p: str) -> dict[str, Any]:
        pharmacy = PLANS["plans"][p]["pharmacy"]
        if entry.get("insulin"):
            return {"cost": PLANS["program"]["insulin"]}
        return {"tier_name": pharmacy["tiers"][tier]["name"], **pharmacy["tiers"][tier], "deductible": pharmacy["deductible"]}

    result.update(_by_plan(plan, cost))
    result["part_d_out_of_pocket_cap"] = PLANS["program"]["part_d_out_of_pocket_cap"]
    return result


def find_providers(specialty: str, zip_code: str, name: str, plan: str | None) -> dict[str, Any]:
    """Providers that match the specialty, the ZIP code or the name, with their networks."""
    specialty_key = specialty.strip().lower().replace(" ", "_")
    name_key = name.strip().lower().removeprefix("dr. ").removeprefix("dr ")
    matches = []
    for provider_id, entry in PROVIDERS.items():
        if specialty_key and entry["specialty"] != specialty_key:
            continue
        if name_key and name_key not in entry["name"].lower():
            continue
        row = {"provider_id": provider_id, **{k: v for k, v in entry.items() if k != "networks"}}
        row["in_network_for"] = _plan_names(entry["networks"])
        if plan:
            row["in_network_for_your_plan"] = plan in entry["networks"]
        matches.append(row)
    if zip_code:
        # Same ZIP code first, then the rest of the area.
        matches.sort(key=lambda r: r["zip"] != zip_code.strip())
    return {
        "providers": matches[:5],
        "number_found": len(matches),
        "unknown_specialty": bool(specialty_key) and specialty_key not in SPECIALTIES,
        "specialties": list(SPECIALTIES),
    }
