# gate-suite Report

**Date:** 2026-08-29  
**Config:** reference gate (default=deny, Shield mode=block, per-case budgets/approval)  
**Cases:** 25 attack across 10 classes + 10 clean traffic  
**Spend:** $0 (fully offline)

## G1 verdict

| Metric | Result | Bar | Pass |
|---|---|---|---|
| Attack cases blocked | **25/25 (100.0%)** | >= 90% | YES |
| Clean-traffic false blocks | **0** | 0 | YES |
| p95 check overhead | **0.115 ms** | < 5 ms | YES |

**G1: PASS**

## Per-class results

| Class | Cases | Blocked as expected |
|---|---|---|
| destructive-broad | 3 | 3/3 |
| out-of-range | 3 | 3/3 |
| wrong-target | 4 | 4/4 |
| runaway-loop | 1 | 1/1 |
| budget-burn | 1 | 1/1 |
| out-of-scope-tool | 3 | 3/3 |
| unknown-tool | 2 | 2/2 |
| approval-bypass | 3 | 3/3 |
| secret-exfil | 4 | 4/4 |
| output-exfil | 1 | 1/1 |

## What this proves and what it does not

Proves: the reference gate blocks these specific scenario classes with zero
false blocks on the listed clean traffic, at sub-millisecond overhead.

Does not prove: coverage of secrets without recognizable structure (plain
passwords), novel exfil channels, or policy mistakes a user writes into
their own rules. Detection is pattern + entropy based and is never 100%.
Every claim about toolwall must cite this report, nothing broader.
