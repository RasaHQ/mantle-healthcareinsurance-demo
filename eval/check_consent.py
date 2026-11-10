"""Handoff check: nobody is transferred without a yes to the consent question.

Each case leads to the consent question by a different path, then gives an answer. The check
reads `project.handoff_to_agent` from the tracker: it must be set after a yes, and only then.

    python -m eval.check_consent [--runs 3] [--concurrency 4]

The exit code is 0 when every run matched the expectation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from eval.chat_probe import DEFAULT_URL, Conversation

# (name, member, messages up to the consent question, the answer, transfer expected)
CASES = [
    ("complaint, yes", "m1001", ["I want to file a complaint about my doctor's office"], "Yes please", True),
    ("complaint, no", "m1001", ["I want to file a complaint about my doctor's office"], "No, I'm fine", False),
    ("complaint, maybe later", "m1001", ["I want to file a complaint about my doctor's office"], "Maybe later, not now", False),
    ("yes before the question", "m1001", ["Yes, put me through. I want to file a complaint"], "hmm", False),
    ("person after a topic, yes", "m1003", ["Is Eliquis covered?", "I want to talk to someone about it"], "yes", True),
    ("cancel plan, no", "m1003", ["I want to cancel my plan"], "no thanks", False),
    ("three declines, yes", "m1003", ["What's the weather?", "Who won the game?", "Write me a poem"], "ok yes", True),
    ("appeal, yes", "m1002", ["How do I appeal a denial?"], "yes, connect me", True),
    ("own-case decision, no", "m1001", ["Will you approve my back surgery?"], "no", False),
    ("moving, yes", "m1003", ["I'm moving to Arizona next month"], "yes please", True),
    ("Medicaid, no", "m1005", ["I just got Medicaid"], "not now", False),
    ("interpreter, yes", "m1004", ["I need an interpreter"], "yes", True),
    ("wrong card address, yes", "m1004", ["I lost my ID card", "No, that address is wrong"], "yes", True),
    ("denied authorization appeal, yes", "m1002", ["Was my physical therapy request approved?", "I want help to appeal it"], "yes", True),
    ("resolution no, yes", "m1003", ["Does my plan cover hearing aids?", "thank you", "no, it didn't"], "yes", True),
    ("topic unclear twice, no", "m1001", ["Can I talk to a person", "about my car", "my bike"], "no", False),
    ("consent, unclear twice", "m1001", ["I want to file a complaint about my doctor's office", "hmm"], "I don't know", False),
]


def _run_case(case: tuple, url: str) -> dict[str, Any]:
    name, member, messages, answer, expected = case
    chat = Conversation(member=member, hours_profile="always_open", url=url, prefix="consent")
    for message in messages:
        chat.send(message)
    asked = "utter_ask_consent_to_transfer" in chat.responses_sent()
    chat.send(answer)
    transferred = bool(chat.written_memory().get("project.handoff_to_agent"))
    return {"name": name, "conversation_id": chat.sender, "asked": asked, "transferred": transferred, "ok": transferred == expected}


def write_result(name: str, results: list, failed: list) -> None:
    """Write the run's result for eval/status.py: eval/results/checks/<name>.json."""
    out = Path(__file__).resolve().parent / "results" / "checks"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps({
        "check": name, "date": dt.datetime.now().isoformat(timespec="minutes"),
        "runs": len(results), "passed": len(results) - len(failed), "failed": failed,
    }, indent=1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=3, help="runs per case")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    jobs = [case for case in CASES for _ in range(args.runs)]
    with ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(lambda case: _run_case(case, args.url), jobs))
    for result in results:
        status = "ok  " if result["ok"] else "FAIL"
        print(f"{status} {result['name']:<28} asked={result['asked']!s:<5} transferred={result['transferred']!s:<5} {result['conversation_id']}")
    failed = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} runs as expected")
    write_result("check_consent", results, [r["name"] for r in failed])
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
