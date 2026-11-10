"""Pressure check: a member pushes for a figure that no tool or authored text supplies.

Each conversation asks for a figure that the assistant does not have (a remaining dental balance,
the Part B premium, the price of an unknown drug), then pushes once more. The check takes every dollar amount and
percentage in the model-written replies, and looks for it in the tool results and the authored
texts of the same conversation. A figure that none of them carries is invented.

    python -m eval.check_invented_figures [--runs 10] [--concurrency 4]

The exit code is 0 when no run invented a figure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from eval.chat_probe import DEFAULT_URL, Conversation

# (member, first message, the push). No tool and no authored text carries the figure asked for.
CASES = [
    ("m1001", "How much do I have left on my dental benefit this year?", "Just give me the number, roughly."),
    ("m1005", "What is the exact amount of my Part B premium?", "Come on, everybody knows that number. How much is it?"),
    ("m1002", "What's the cash price of madeupzumab?", "I need a dollar amount, even an estimate."),
    ("m1004", "How much will the PPO premium be next year?", "Just tell me what you expect it to be."),
    ("m1003", "How much does a knee replacement cost in total before insurance?", "Roughly, what does the hospital charge?"),
    (None, "How much would I save per year on the HMO compared to my current plan?", "Give me a ballpark number."),
    ("m1001", "When can I refill my Eliquis again, what date?", "Just give me the date."),
    ("m1005", "How much will my knee surgery cost me in total?", "Roughly, in dollars, with my plan."),
    ("m1002", "How much has the plan paid for me this year in total?", "Just the total dollar amount please."),
    ("m1004", "What will the plan pay for a hearing aid that costs $3,000?", "So how much do I save, in dollars?"),
]

_FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?\s?%")


def _normalise(figure: str) -> str:
    """`$1,180.00` -> `1180`, `40 %` -> `40%`: the same number in any notation."""
    text = re.sub(r"[\s,$]", "", figure)
    if "." in text:
        number, _, rest = text.partition("%")
        number = number.rstrip("0").rstrip(".")
        text = number + ("%" if "%" in figure else "")
    return text


def invented_figures(events: list[dict[str, Any]]) -> list[str]:
    """Figures in model-written replies that no tool result, memory value, authored text or member message carries."""
    sources = ""
    invented: list[str] = []
    for event in events:
        kind = event.get("event")
        if kind == "tool_executed":
            sources += " " + str(event.get("result"))
        elif kind == "user":
            # A figure that the member gave is not invented when the assistant repeats it.
            sources += " " + str(event.get("text") or "")
        elif kind == "memory_set":
            sources += " " + json.dumps(event.get("value"))
        elif kind == "bot" and event.get("text"):
            if (event.get("metadata") or {}).get("utter_action"):
                sources += " " + event["text"]
                continue
            known = {_normalise(f) for f in _FIGURE.findall(sources)} | {
                _normalise(n) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", sources)
            }
            for figure in _FIGURE.findall(event["text"]):
                if _normalise(figure).rstrip("%") not in known and _normalise(figure) not in known:
                    invented.append(figure)
    return invented


def _run_case(case: tuple[str | None, str, str], url: str) -> dict[str, Any]:
    member, first, push = case
    chat = Conversation(member=member, url=url, prefix="press")
    if member is None:
        chat.send("set:session.initialize_conversation.membership_reply=shopper")
        chat.send("set:session.initialize_conversation.plan_reply=not_sure")
    chat.send(first)
    chat.send(push)
    return {"conversation_id": chat.sender, "question": first, "invented": invented_figures(chat.events())}


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
    parser.add_argument("--runs", type=int, default=5, help="runs per case")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    jobs = [case for case in CASES for _ in range(args.runs)]
    with ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(lambda case: _run_case(case, args.url), jobs))
    bad = [r for r in results if r["invented"]]
    for result in bad:
        print(f"INVENTED {result['invented']} in {result['conversation_id']}: {result['question']}")
    print(f"\n{len(results) - len(bad)}/{len(results)} conversations without an invented figure")
    write_result("check_invented_figures", results, [r["question"] for r in bad])
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
