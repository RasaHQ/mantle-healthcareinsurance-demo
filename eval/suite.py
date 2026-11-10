"""Run the scenario suite against the running assistant, then the grounding judge.

    python -m eval.suite [--url http://localhost:5005] [--run-count 3] [--concurrency 4]
                             [--glob 'grounding/*.yml'] [--stamp <name>] [--no-grounding]

Each scenario is a member goal (eval/scenarios/*/*.yml). The framework's simulator plays the member,
and its judge scores the transcript against the scenario's criteria; the assertions are checked on
the tracker. A scenario signs in through `setup.initial_slots`: `member_id`, `surface` and
`hours_profile` are project fields with `seed: true`, so the framework sends them on the session
start, as a channel client does.

Results land in eval/results/<stamp>/: one run_N.txt per run and scenario, summary.json and
summary.txt. After the suite, the grounding judge (eval/grounding_judge.py) checks every message
that the model wrote against what the model could see; its report lands in
eval/results/<stamp>/grounding/. Its flags are candidates for review and do not change the exit code.

The exit code is 0 when every run of every scenario passed.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
from pathlib import Path

from rasa.builder.copilot.mcp_server.tools import evaluate_agent
from rasa.builder.copilot.mcp_server.tools.artifact_writer import write_experiment_summary
from rasa.builder.copilot.mcp_server.tools.eval_config import build_llm_client, load_conftest, load_prompt_template
from rasa.builder.copilot.mcp_server.tools.scenario import load_scenario
from rasa.cli.project_env import load_project_dotenv

from eval import grounding_judge

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = REPO_ROOT / "eval" / "scenarios"


async def _run_case(args: argparse.Namespace) -> int:
    conftest = load_conftest(REPO_ROOT)
    prompts = {
        key: load_prompt_template(REPO_ROOT, ref) if ref else None
        for key, ref in (
            ("simulated_user_prompt", conftest.simulation.simulated_user_prompt),
            ("criteria_judge_prompt", conftest.evaluation.criteria_judge_prompt),
            ("metrics_judge_prompt", conftest.evaluation.metrics_judge_prompt),
        )
    }
    paths = sorted(SCENARIOS.glob(args.glob))
    if not paths:
        print(f"no scenarios match {args.glob!r}", file=sys.stderr)
        return 2
    stamp = args.stamp or dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    entries, elapsed = await evaluate_agent.run_scenarios(
        scenarios=[load_scenario(path) for path in paths],
        project_path=REPO_ROOT,
        experiment_timestamp=stamp,
        run_count=args.run_count,
        parallelism=args.concurrency,
        rasa_server_url=args.url,
        simulation_llm_client=build_llm_client(conftest.simulation.llm),
        eval_llm_client=build_llm_client(conftest.evaluation.llm),
        eval_llm_config=conftest.evaluation.llm,
        simulation_max_concurrent_llm_calls=conftest.simulation.max_concurrent_llm_calls,
        eval_max_concurrent_llm_calls=conftest.evaluation.max_concurrent_llm_calls,
        **prompts,
    )
    write_experiment_summary(REPO_ROOT, stamp, entries, wall_clock_s=elapsed)

    passed = 0
    for path, entry in zip(paths, entries):  # run_scenarios keeps the input order
        ok = entry.runs_passed == entry.runs_total
        passed += ok
        errors = f"  ({entry.runs_errored} harness errors)" if entry.runs_errored else ""
        name = path.relative_to(SCENARIOS).with_suffix("")
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {entry.runs_passed}/{entry.runs_total}{errors}")
    results = REPO_ROOT / "eval" / "results" / stamp
    print(f"\n{passed}/{len(entries)} scenarios passed every run, in {elapsed:.0f}s. Results: {results}")

    if not args.no_grounding:
        runs = sorted(results.glob("*/run_*.txt"))
        grounding_judge.main(["--ids-from", *map(str, runs), "--url", args.url, "--out", str(results / "grounding")])
    return 0 if passed == len(entries) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:5005")
    parser.add_argument("--run-count", type=int, default=1, help="runs per scenario")
    parser.add_argument("--concurrency", type=int, default=4, help="runs in flight at once")
    parser.add_argument("--glob", default="*/*.yml", help="relative to eval/scenarios, for example 'adversarial/*.yml'")
    parser.add_argument("--stamp", default="", help="results folder name; default: the current time")
    parser.add_argument("--no-grounding", action="store_true", help="skip the grounding judge")
    load_project_dotenv(str(REPO_ROOT))
    return asyncio.run(_run_case(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
