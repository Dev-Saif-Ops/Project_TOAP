"""Main benchmark orchestrator.

Usage:
    python runner/benchmark.py --runs 5 --tier 1
    python runner/benchmark.py --runs 50 --model gpt-4o --condition few_shot_2
    python runner/benchmark.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from toap import TOAPParser
from adapters.gemini_adapter import GeminiAdapter

load_dotenv(ROOT / ".env")

PROMPTS_DIR = ROOT / "prompts"
TASKS_FILE = ROOT / "tasks" / "test_cases.yaml"
RESULTS_DIR = ROOT / "results"

CONDITIONS = ["zero_shot", "few_shot_2", "few_shot_5"]

GATES = {
    "G1_compliance": {"threshold": 0.90, "label": "Few-shot compliance"},
    "G2_accuracy": {"threshold": 0.85, "label": "Semantic accuracy"},
    "G3_savings": {"threshold": 0.35, "label": "Token savings"},
    "G4_reliability": {"threshold": 0.85, "label": "End-to-end success"},
}


def load_tasks(tier: int | None = None) -> list[dict]:
    with open(TASKS_FILE) as f:
        tasks = yaml.safe_load(f)
    if tier is not None:
        tasks = [t for t in tasks if t["tier"] <= tier]
    return tasks


def load_prompt(condition: str) -> str:
    path = PROMPTS_DIR / f"{condition}.txt"
    return path.read_text(encoding="utf-8")


def build_json_baseline(task: dict) -> str:
    """Generate equivalent JSON for compression comparison."""
    exp = task["expected"]
    payload = {
        "thought": exp.get("thought"),
        "action": exp["namespace"],
        "params": exp["args"],
    }
    return json.dumps(payload, indent=2)


def validate_semantic(parsed_args: dict, expected: dict) -> tuple[bool, list[str]]:
    """Semantic validation against ground truth with alias-normalized args."""
    issues = []

    # Thought domain is an optional attention anchor — not validated strictly.

    if parsed_args.get("namespace") != expected["namespace"]:
        issues.append(
            f"namespace: got {parsed_args.get('namespace')!r}, expected {expected['namespace']!r}"
        )

    actual_args = parsed_args.get("args", {})
    for key, val in expected["args"].items():
        actual = actual_args.get(key)
        if isinstance(val, str) and isinstance(actual, str):
            if actual.lower() == val.lower():
                continue
        if actual != val:
            issues.append(f"arg {key}: got {actual!r}, expected {val!r}")

    must_not = expected.get("must_not_contain")
    if must_not:
        raw_args_str = str(actual_args)
        if must_not.lower() in raw_args_str.lower():
            issues.append(f"must_not_contain violated: found {must_not!r}")

    return len(issues) == 0, issues


def run_single(
    adapter,
    parser: TOAPParser,
    task: dict,
    condition: str,
    run_id: int,
) -> dict:
    prompt_template = load_prompt(condition)
    system_prompt = prompt_template.replace("{task_description}", task["description"])
    user_prompt = "Execute the task above. Respond in TOAP format only."

    response = adapter.complete(system_prompt, user_prompt)
    parsed = parser.parse(response.output)
    parsed_dict = parsed.to_dict()

    semantic_ok, semantic_issues = False, []
    if parsed.valid:
        semantic_ok, semantic_issues = validate_semantic(parsed_dict, task["expected"])

    json_baseline = build_json_baseline(task)
    json_tokens = adapter.count_tokens(json_baseline)
    toap_tokens = response.completion_tokens

    savings_pct = 0.0
    if json_tokens > 0 and parsed.valid:
        savings_pct = round((1 - toap_tokens / json_tokens) * 100, 1)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task["id"],
        "tier": task["tier"],
        "model": response.model,
        "condition": condition,
        "run_id": run_id,
        "raw_output": response.output,
        "compliance": parsed.valid,
        "semantic_correct": semantic_ok,
        "semantic_issues": semantic_issues,
        "toap_tokens": toap_tokens,
        "json_tokens": json_tokens,
        "savings_pct": savings_pct,
        "prompt_tokens": response.prompt_tokens,
        "total_tokens": response.total_tokens,
        "latency_ms": round(response.latency_ms, 1),
        "parse_errors": [e.message for e in parsed.errors],
    }


def compute_summary(results: list[dict]) -> dict:
    if not results:
        return {}

    total = len(results)
    if total == 0:
        return {}

    compliant = sum(1 for r in results if r.get("compliance"))
    semantic = sum(1 for r in results if r.get("semantic_correct"))
    savings = [r["savings_pct"] for r in results if r.get("compliance") and r.get("savings_pct", 0) > 0]
    latencies = [r["latency_ms"] for r in results if "latency_ms" in r]

    return {
        "total_runs": total,
        "compliance_rate": round(compliant / total, 3),
        "semantic_accuracy": round(semantic / total, 3),
        "semantic_when_compliant": round(
            sum(1 for r in results if r["semantic_correct"]) / max(compliant, 1), 3
        ),
        "avg_savings_pct": round(sum(savings) / max(len(savings), 1), 1),
        "median_savings_pct": round(sorted(savings)[len(savings) // 2], 1) if savings else 0,
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 1),
    }


def print_report(summaries: dict[str, dict], results: list[dict]):
    print("\n" + "=" * 60)
    print("  TOAP BENCHMARK RESULTS")
    print("=" * 60)

    for key, summary in summaries.items():
        print(f"\n{key}")
        print("-" * 60)
        if not summary:
            print("  No successful results.")
            continue
        print(f"  Compliance rate     : {summary['compliance_rate']*100:.1f}%")
        print(f"  Semantic accuracy   : {summary['semantic_accuracy']*100:.1f}%")
        print(f"  Accuracy (compliant): {summary['semantic_when_compliant']*100:.1f}%")
        print(f"  Avg token savings   : {summary['avg_savings_pct']:.1f}%")
        print(f"  Avg latency         : {summary['avg_latency_ms']:.0f}ms")

    print("\n" + "=" * 60)
    print("  GO / NO-GO VERDICT")
    print("=" * 60)

    few_shot_results = [r for r in results if r["condition"] in ("few_shot_2", "few_shot_5")]
    if not few_shot_results:
        print("  WARNING: No few-shot results to evaluate gates.")
        return

    fs_summary = compute_summary(few_shot_results)
    if not fs_summary:
        print("  WARNING: All few-shot runs failed. Check API key and model access.")
        return
    gates = {
        "G1": fs_summary["compliance_rate"] >= GATES["G1_compliance"]["threshold"],
        "G2": fs_summary["semantic_when_compliant"] >= GATES["G2_accuracy"]["threshold"],
        "G3": fs_summary["avg_savings_pct"] / 100 >= GATES["G3_savings"]["threshold"],
        "G4": fs_summary["semantic_accuracy"] >= GATES["G4_reliability"]["threshold"],
    }

    all_pass = all(gates.values())
    for gate, passed in gates.items():
        icon = "[PASS]" if passed else "[FAIL]"
        print(f"  {icon} {gate}: {'PASS' if passed else 'FAIL'}")

    print()
    if all_pass:
        print("  >> GO -- Proceed to Phase 1 (SDK + CLI)")
    elif gates["G1"] and gates["G2"]:
        print("  >> MARGINAL -- Compliance OK but savings/reliability weak. Review before GO.")
    else:
        print("  >> NO-GO -- Core bet failed. Consider JSON minification pivot.")
    print("=" * 60 + "\n")


def main():
    parser_cli = argparse.ArgumentParser(description="TOAP Benchmark Runner")
    parser_cli.add_argument("--runs", type=int, default=5, help="Runs per task/condition/model")
    parser_cli.add_argument("--tier", type=int, default=1, help="Max tier to include (1-4)")
    parser_cli.add_argument(
        "--model",
        choices=["gpt-4o", "claude-3-5-sonnet", "gemini", "all"],
        default="all",
    )
    parser_cli.add_argument(
        "--condition",
        choices=CONDITIONS + ["all"],
        default="all",
    )
    parser_cli.add_argument("--dry-run", action="store_true", help="Parse tasks only, no API calls")
    args = parser_cli.parse_args()

    tasks = load_tasks(tier=args.tier)
    print(f"Loaded {len(tasks)} tasks (tier <= {args.tier})")

    if args.dry_run:
        toap_parser = TOAPParser()
        for task in tasks:
            print(f"  [{task['tier']}] {task['id']}: {task['description'][:60]}...")
        print("\nDry run complete. No API calls made.")
        return

    adapters = []
    if args.model in ("gemini", "all"):
        if not os.environ.get("GEMINI_API_KEY"):
            print("WARNING: GEMINI_API_KEY not set, skipping Gemini")
        else:
            adapters.append((os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), GeminiAdapter()))
    if args.model in ("gpt-4o", "all"):
        if not os.environ.get("OPENAI_API_KEY"):
            print("WARNING: OPENAI_API_KEY not set, skipping GPT-4o")
        else:
            from adapters.openai_adapter import OpenAIAdapter
            adapters.append(("gpt-4o", OpenAIAdapter()))
    if args.model in ("claude-3-5-sonnet", "all"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("WARNING: ANTHROPIC_API_KEY not set, skipping Claude 3.5")
        else:
            from adapters.anthropic_adapter import AnthropicAdapter
            adapters.append(("claude-3-5-sonnet", AnthropicAdapter()))

    if not adapters:
        print("ERROR: No API keys configured. Set GEMINI_API_KEY, OPENAI_API_KEY and/or ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    conditions = CONDITIONS if args.condition == "all" else [args.condition]
    toap_parser = TOAPParser()
    all_results: list[dict] = []

    total_calls = len(tasks) * len(adapters) * len(conditions) * args.runs
    print(f"Starting benchmark: {total_calls} API calls estimated\n")

    for model_name, adapter in adapters:
        for condition in conditions:
            for task in tasks:
                for run_id in range(1, args.runs + 1):
                    print(
                        f"  [{model_name}] {condition} | {task['id']} | run {run_id}/{args.runs}",
                        end=" ... ",
                        flush=True,
                    )
                    try:
                        result = run_single(adapter, toap_parser, task, condition, run_id)
                        all_results.append(result)
                        status = "OK" if result["compliance"] else "FAIL"
                        print(f"{status} ({result['latency_ms']:.0f}ms)")
                    except Exception as e:
                        err_str = str(e)
                        print(f"ERROR: {err_str[:80]}")
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            print("  (rate limit — waiting 45s...)")
                            time.sleep(45)
                            try:
                                result = run_single(adapter, toap_parser, task, condition, run_id)
                                all_results.append(result)
                                status = "OK" if result["compliance"] else "FAIL"
                                print(f"  retry: {status} ({result['latency_ms']:.0f}ms)")
                                continue
                            except Exception as e2:
                                err_str = str(e2)
                        all_results.append({
                            "task_id": task["id"],
                            "model": model_name,
                            "condition": condition,
                            "run_id": run_id,
                            "compliance": False,
                            "semantic_correct": False,
                            "latency_ms": 0,
                            "error": err_str[:200],
                        })
                    time.sleep(4)

    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = RESULTS_DIR / f"benchmark_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)

    csv_path = RESULTS_DIR / f"benchmark_{ts}.csv"
    if all_results:
        all_keys: set[str] = set()
        for row in all_results:
            all_keys.update(row.keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(all_results)

    summaries = {}
    for model_name, _ in adapters:
        for condition in conditions:
            key = f"{model_name} / {condition}"
            subset = [
                r for r in all_results
                if r.get("model", "").startswith(model_name.split("-")[0])
                and r.get("condition") == condition
                and "error" not in r
            ]
            summaries[key] = compute_summary(subset)

    print_report(summaries, all_results)
    print(f"Results saved:\n  {json_path}\n  {csv_path}")


if __name__ == "__main__":
    main()
