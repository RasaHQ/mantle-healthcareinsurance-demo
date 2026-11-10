"""Grounding judge: every message that the model wrote, checked against what the model could see.

The scenario judge sees the transcript and the names of the tools, but not the tool results. This
judge sees, for each model-written message: the tool results so far, the memory so far, the
authored responses that were sent, and the skills and tools of the assistant. It lists every
statement in the message that none of these carries, each with a class:

- member_fact: a claim about this member's own coverage, costs, claims, authorizations or details
- domain_generic: a general claim about health insurance or about the insurer's products
- capability_within: an offer to do something that a skill or tool does
- capability_beyond: an offer to do something that no skill or tool does
- other

member_fact and capability_beyond are the ones that matter. A flag is a candidate for review,
not a verdict.

    python -m eval.grounding_judge --ids-from eval/results/<stamp>/*/run_*.txt [--judge-model gpt-6-luna]

The conversations must still be in the server's tracker store.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI
from rasa.cli.project_env import load_project_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
_CONVERSATION_ID = re.compile(r"\b(sim-[0-9a-f-]{36}|[a-z]+-[0-9a-f]{8})\b")

GROUNDING_PROMPT = """You check one reply of a Medicare Advantage member services chat assistant against the sources it had.

SOURCES (everything the assistant could draw on at this point):
{sources}

MEMBER'S MESSAGES SO FAR:
{member}

ASSISTANT REPLY TO CHECK:
{reply}

List every statement in the reply that none of the sources carries. A statement is a claim about
coverage, benefits, costs, limits, drugs, prior authorizations, claims, dates, documents, links,
places to look, procedures, eligibility, or the member's own details. A paraphrase of a source is
fine. A question, an offer, an apology or an acknowledgement is not a statement. Something the
member said is a source for that fact. A tool result's own instructions (`next_step`, `note`,
`not_in_this_data`) count as sources.

Give each unsupported statement one class:
- member_fact: a claim about this member's own coverage, costs, claims, authorizations or details
- domain_generic: a general claim about health insurance or the insurer's products
- capability_within: an offer to do something that a listed skill or tool does
- capability_beyond: an offer to do something that no listed skill or tool does
- other

Answer as JSON only:
{{"unsupported": [{{"statement": "<quote>", "class": "<class>", "why": "<one sentence>"}}], "note": "<one sentence>"}}
If a source carries everything, return {{"unsupported": [], "note": "..."}}."""


def _skills_and_tools() -> list[str]:
    """What the assistant is built to do: each skill's description and prose, and each tool's description."""
    out = []
    for skill_md in sorted(REPO_ROOT.glob("skills/*/skill.md")):
        text = skill_md.read_text()
        parts = text.split("---", 2)
        front = yaml.safe_load(parts[1]) if len(parts) == 3 else {}
        prose = re.sub(r":::ordered_block.*?:::", "", parts[2] if len(parts) == 3 else text, flags=re.S).strip()
        out.append(f"[skill {skill_md.parent.name}] {(front or {}).get('description', '')}\n{prose}")
    for tools_py in sorted(REPO_ROOT.glob("skills/*/tools.py")):
        for match in re.finditer(r'description\s*=\s*\(?\s*((?:f?"[^"]*"\s*)+)', tools_py.read_text()):
            out.append(f"[tool, {tools_py.parent.name}] " + " ".join(re.findall(r'"([^"]*)"', match.group(1))))
    return out


def _tracker_events(url: str, conversation_id: str) -> list[dict[str, Any]]:
    with urllib.request.urlopen(f"{url}/conversations/{conversation_id}/tracker?include_events=ALL", timeout=60) as r:
        return json.loads(r.read().decode()).get("events") or []


def model_written_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each bot message without an authored response name, with the sources visible at that moment."""
    sources: list[str] = []
    member: list[str] = []
    out = []
    for event in events:
        kind = event.get("event")
        if kind == "user" and event.get("text") and event["text"] != "/session_start":
            member.append(event["text"])
        elif kind == "tool_executed":
            sources.append(f"[tool {event.get('tool_name')} {json.dumps(event.get('arguments') or {})}] -> {event.get('result')}")
        elif kind == "memory_set" and event.get("value") not in (None, "", [], {}):
            sources.append(f"[memory {event.get('key')}] {json.dumps(event.get('value'))[:400]}")
        elif kind == "bot" and event.get("text"):
            response = (event.get("metadata") or {}).get("utter_action")
            if response:
                sources.append(f"[authored {response}] {event['text']}")
            else:
                out.append({"reply": event["text"], "sources": list(sources), "member": list(member), "turn": len(member)})
    return out


def _ask_judge(client: OpenAI, model: str, message: dict[str, Any], skills: list[str]) -> dict[str, Any]:
    sources = "\n".join(message["sources"]) + "\n\n[skills and tools]\n" + "\n".join(skills)
    prompt = GROUNDING_PROMPT.format(
        sources=sources[:60000],
        member="\n".join(f"- {m}" for m in message["member"]),
        reply=message["reply"],
    )
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}
    )
    try:
        return json.loads(response.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        return {"unsupported": [{"statement": "<the judge returned no JSON>", "class": "other", "why": ""}], "note": ""}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids-from", nargs="+", required=True, help="files to take conversation ids from")
    parser.add_argument("--url", default="http://localhost:5005")
    parser.add_argument("--judge-model", default="gpt-6-luna")
    parser.add_argument("--out", default="", help="report folder; default eval/results/grounding_<stamp>")
    args = parser.parse_args(argv)
    load_project_dotenv(str(REPO_ROOT))

    ids: list[str] = []
    for name in args.ids_from:
        for found in _CONVERSATION_ID.findall(Path(name).read_text(errors="replace")):
            if found not in ids:
                ids.append(found)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = Path(args.out) if args.out else REPO_ROOT / "eval" / "results" / f"grounding_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    client = OpenAI()
    skills = _skills_and_tools()
    rows: list[dict[str, Any]] = []
    missing = 0
    for conversation_id in ids:
        try:
            events = _tracker_events(args.url.rstrip("/"), conversation_id)
        except Exception:  # noqa: BLE001 - a missing conversation is counted, not fatal
            missing += 1
            continue
        for message in model_written_messages(events):
            verdict = _ask_judge(client, args.judge_model, message, skills)
            unsupported = verdict.get("unsupported") or []
            rows.append({"conversation_id": conversation_id, **message, "unsupported": unsupported, "note": verdict.get("note", "")})
            classes = {item.get("class", "other") for item in unsupported}
            flag = "FLAG" if classes & {"member_fact", "capability_beyond"} else ("note" if classes else "ok  ")
            print(f"{flag} {conversation_id} turn {message['turn']}: {message['reply'][:90]!r}")

    by_class: dict[str, int] = {}
    for row in rows:
        for item in row["unsupported"]:
            by_class[item.get("class", "other")] = by_class.get(item.get("class", "other"), 0) + 1
    flagged = [row for row in rows if row["unsupported"]]
    (out_dir / "sweep.json").write_text(json.dumps(rows, indent=1))

    lines = [
        f"# Grounding report {stamp}",
        "",
        f"Conversations found: {len(ids) - missing} of {len(ids)}. Model-written messages: {len(rows)}. "
        f"Messages with a flag: {len(flagged)}. Statements by class: {json.dumps(by_class)}. Judge: {args.judge_model}.",
        "",
    ]
    for row in flagged:
        lines += [f"## {row['conversation_id']}, turn {row['turn']}", "", "> " + row["reply"].replace("\n", "\n> "), ""]
        lines += [f"- [{u.get('class', 'other')}] {u.get('statement')}: {u.get('why')}" for u in row["unsupported"]]
        lines += ["", "<details><summary>Sources</summary>", "", "```", *[s[:600] for s in row["sources"]], "```", "</details>", ""]
    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"\nmodel-written messages {len(rows)}, flagged {len(flagged)}, by class {by_class}")
    print(f"report: {out_dir / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
