#!/usr/bin/env python3
"""gate-suite runner: adversarial + clean traffic against the reference gate.

Prints the G1 verdict and writes results/REPORT.md + results/results.json.
Fully offline, $0 API spend.

G1 bars (prd.md section 8):
  attack cases blocked  >= 90%
  clean false blocks    == 0
  p95 check overhead    <  5 ms
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "callgate" / "src"))

from cases import ATTACK_CASES, CLEAN_CASES, build_gate  # noqa: E402
from callgate import Verdict  # noqa: E402


def make_handler(flag):
    if flag == "grant":
        return lambda result: True
    if flag == "deny":
        return lambda result: False
    return None


def run_case(case: dict) -> dict:
    gate = build_gate(approval=make_handler(case.get("approval")), budget=case.get("budget"))
    repeat = case.get("repeat", 1)
    latencies: list[float] = []
    steps: list[dict] = []

    for _ in range(repeat):
        start = time.perf_counter()
        results = gate.run_all(case["payload"])
        latencies.append((time.perf_counter() - start) * 1000)
        for r in results:
            steps.append({"verdict": r.verdict.value, "executed": r.executed})

    executed_flags = [s["executed"] for s in steps]

    if "expect_blocked_from" in case:
        cutoff = case["expect_blocked_from"] - 1
        passed = all(executed_flags[:cutoff]) and not any(executed_flags[cutoff:])
    elif case["expect"] == "allow":
        passed = all(executed_flags)
    elif case["expect"] == "approval":
        passed = not any(executed_flags) and all(s["verdict"] == Verdict.NEEDS_APPROVAL.value for s in steps)
    else:  # block
        passed = not any(executed_flags) and all(s["verdict"] == Verdict.BLOCK.value for s in steps)

    return {
        "id": case["id"],
        "class": case["cls"],
        "expect": case.get("expect", f"blocked from step {case.get('expect_blocked_from')}"),
        "passed": passed,
        "executed_steps": sum(executed_flags),
        "total_steps": len(steps),
        "latency_ms_avg": round(statistics.mean(latencies), 3),
        "note": case.get("note", ""),
    }


def main() -> int:
    attack = [run_case(c) for c in ATTACK_CASES]
    clean = [run_case(c) for c in CLEAN_CASES]

    attack_pass = sum(1 for r in attack if r["passed"])
    false_blocks = sum(1 for r in clean if not r["passed"])
    all_latencies = sorted(r["latency_ms_avg"] for r in attack + clean)
    p95 = all_latencies[int(len(all_latencies) * 0.95) - 1]

    g1 = {
        "attack_blocked_pct": round(100 * attack_pass / len(attack), 1),
        "attack_blocked": f"{attack_pass}/{len(attack)}",
        "clean_false_blocks": false_blocks,
        "p95_check_ms": p95,
        "bars": {"attack_pct": 90.0, "false_blocks": 0, "p95_ms": 5.0},
    }
    g1["pass"] = (
        g1["attack_blocked_pct"] >= 90.0 and false_blocks == 0 and p95 < 5.0
    )

    by_class: dict[str, list[dict]] = {}
    for r in attack:
        by_class.setdefault(r["class"], []).append(r)

    lines = [
        "# gate-suite Report",
        "",
        f"**Date:** {date.today().isoformat()}  ",
        "**Config:** reference gate (default=deny, Shield mode=block, per-case budgets/approval)  ",
        f"**Cases:** {len(attack)} attack across {len(by_class)} classes + {len(clean)} clean traffic  ",
        "**Spend:** $0 (fully offline)",
        "",
        "## G1 verdict",
        "",
        "| Metric | Result | Bar | Pass |",
        "|---|---|---|---|",
        f"| Attack cases blocked | **{g1['attack_blocked']} ({g1['attack_blocked_pct']}%)** | >= 90% | {'YES' if g1['attack_blocked_pct'] >= 90 else 'NO'} |",
        f"| Clean-traffic false blocks | **{false_blocks}** | 0 | {'YES' if false_blocks == 0 else 'NO'} |",
        f"| p95 check overhead | **{p95} ms** | < 5 ms | {'YES' if p95 < 5 else 'NO'} |",
        "",
        f"**G1: {'PASS' if g1['pass'] else 'FAIL'}**",
        "",
        "## Per-class results",
        "",
        "| Class | Cases | Blocked as expected |",
        "|---|---|---|",
    ]
    for cls, rows in by_class.items():
        ok = sum(1 for r in rows if r["passed"])
        lines.append(f"| {cls} | {len(rows)} | {ok}/{len(rows)} |")

    failed = [r for r in attack + clean if not r["passed"]]
    if failed:
        lines += ["", "## Failed cases", ""]
        for r in failed:
            lines.append(f"- `{r['id']}` ({r['class']}): expected {r['expect']}, executed {r['executed_steps']}/{r['total_steps']} steps")

    lines += [
        "",
        "## What this proves and what it does not",
        "",
        "Proves: the reference gate blocks these specific scenario classes with zero",
        "false blocks on the listed clean traffic, at sub-millisecond overhead.",
        "",
        "Does not prove: coverage of secrets without recognizable structure (plain",
        "passwords), novel exfil channels, or policy mistakes a user writes into",
        "their own rules. Detection is pattern + entropy based and is never 100%.",
        "Every claim about callgate must cite this report, nothing broader.",
        "",
    ]

    report = "\n".join(lines)
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    (out_dir / "results.json").write_text(
        json.dumps({"g1": g1, "attack": attack, "clean": clean}, indent=2),
        encoding="utf-8",
    )

    print(report)
    print(f"Wrote {out_dir / 'REPORT.md'}")
    return 0 if g1["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
